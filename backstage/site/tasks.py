# Duplicated from dispatcher.tasks to prevent copy-wrong errors...

import requests
import os
import threading
import json
import time
import queue
import traceback
from django.utils import timezone
from django.db import transaction

from dispatcher.models import Server
from django.conf import settings
from problem.models import Problem
from migrate.models import OldSubmission
from submission.util import SubmissionStatus
from utils.url_formatter import upload_linker, judge_linker


_WORKER_THREAD_NUM = 0
_WORKER_QUEUE = queue.Queue()


class Dispatcher:

    def __init__(self, submission_id):
        # The problem and submission are not bound to be the latest one, therefore
        # each time they are updated, remember: ALWAYS REDO THE QUERY AND CHECK TIME
        self.submission_id = submission_id
        # Get, never used...
        self.submission = OldSubmission.objects.get(pk=submission_id)
        self.problem_id = str(self.submission.problem)
        self.server_id = 0

    def get_server(self):
        with transaction.atomic():
            servers = Server.objects.select_for_update().all()
            if servers.exists():
                server = servers.first()
                server.last_seen_time = timezone.now()
                self.server_id = server.pk
                server.save()
                return True
        # If the program goes here, there is no server available
        return False

    def is_latest_data_for_server(self):
        server_status, _ = ServerProblemStatus.objects.get_or_create(
            problem__pk=self.problem_id,
            server__pk=self.server_id,
            defaults={'problem': Problem.objects.get(pk=self.problem_id),
                      'server': Server.objects.get(pk=self.server_id)},
        )
        if server_status.testdata_hash != Problem.objects.get(pk=self.problem_id).testdata_hash:
            return False
        return True

    def update_data_for_server(self):
        if self.is_latest_data_for_server():
            return True
        try:
            file_path = os.path.join(settings.TESTDATA_DIR, str(self.problem_id) + '.zip')
            server = Server.objects.get(pk=self.server_id)
            problem_hash = Problem.objects.get(pk=self.problem_id).testdata_hash
            with open(file_path, 'rb') as f:
                response = requests.post(upload_linker(server.ip, server.port, self.problem_id),
                                         data=f.read(), auth=('token', server.token)).json()
                if response['status'] != 'received':
                    raise SystemError('Remote server rejected data send request.', response['message'])
            with transaction.atomic():
                server_status = ServerProblemStatus.objects.select_for_update().get(problem__pk=self.problem_id,
                                                                                    server__pk=self.server_id)
                server_status.testdata_hash = problem_hash
                server_status.save(update_fields=["testdata_hash"])
            return True
        except FileNotFoundError:
            print('Data file not found. Why?')
            return False
        except Exception as e:
            print('Something wrong during update:')
            print(repr(e))
            return False

    def update_submission_and_problem(self, response):
        with transaction.atomic():
            submission = OldSubmission.objects.select_for_update().get(pk=self.submission_id)
            submission.status = response['verdict']
            submission.judge_end_time = timezone.now()
            if submission.status == SubmissionStatus.COMPILE_ERROR:
                submission.status_detail = response['message']
            else:
                submission.status_detail = json.dumps(response['detail'])
                submission.status_percent = response['score']
                submission.status_time = response['time']
                submission.status_memory = response['memory']
            submission.save()

    def dispatch(self):
        # Attempt: 3 times
        for attempt in range(3):
            try:
                if not self.get_server():
                    raise SystemError('No server available.')
                if not self.update_data_for_server():
                    raise SystemError('Data upload failed.')

                with transaction.atomic():
                    self.submission = OldSubmission.objects.select_for_update().get(pk=self.submission_id)
                    self.submission.judge_start_time = timezone.now()
                    self.submission.status = SubmissionStatus.JUDGING
                    self.submission.save()

                problem = Problem.objects.get(pk=self.problem_id)
                request = {
                    "id": self.submission.pk,
                    "lang": self.submission.lang,
                    "code": self.submission.code,
                    "settings": {
                        "max_time": problem.time_limit,
                        "max_sum_time": problem.sum_time_limit,
                        "max_memory": problem.memory_limit,
                        "problem_id": problem.pk
                    },
                    "judge": problem.judge
                }

                # Request: wait for one hour
                server = Server.objects.get(pk=self.server_id)
                response = requests.post(judge_linker(server.ip, server.port),
                                         json=request, auth=('token', server.token),
                                         timeout=3600).json()
                # print(response)
                if response['status'] != 'received':
                    raise SystemError('Remote server rejected judge request.', response['message'])

                self.update_submission_and_problem(response)
                return True
            except Exception as e:
                print('Something wrong during dispatch of %s.' % str(self.submission_id))
                traceback.print_exc()
            # Wait for 10 seconds
            time.sleep(10)

        with transaction.atomic():
            self.submission = OldSubmission.objects.select_for_update().get(pk=self.submission_id)
            self.submission.status = SubmissionStatus.SYSTEM_ERROR
            self.submission.save()
        return False


class DispatcherThread(threading.Thread):

    def __init__(self, submission_id):
        super().__init__()
        self.submission_id = submission_id

    def run(self):
        global _WORKER_THREAD_NUM, _WORKER_QUEUE
        _WORKER_QUEUE.put(self.submission_id)

        # Low worker count
        if _WORKER_THREAD_NUM <= Server.objects.count() * 24:
            # Thread number within range
            _WORKER_THREAD_NUM += 1
            # print('establishing', _WORKER_THREAD_NUM)
            while True:
                try:
                    item = _WORKER_QUEUE.get_nowait()
                    Dispatcher(item).dispatch()
                except queue.Empty:
                    break
            _WORKER_THREAD_NUM -= 1
            # print('killing', _WORKER_THREAD_NUM)


class OldSubmissionRejudgeThread(threading.Thread):

    def __init__(self, submissions, skip=False):
        """
        :param submissions: pass id
        :param skip: if True then only WAITING, JUDGING and SYSTEM_ERROR subs will be rejudged
        """
        super().__init__()
        self.submissions = submissions
        self.skip = skip

    def run(self):
        for sub in self.submissions:
            if self.skip:
                submission = OldSubmission.objects.get(pk=sub)
                if SubmissionStatus.is_judged(submission.status):
                    continue
            DispatcherThread(sub).start()
