import requests
import os
import threading
import json
import time
import queue
import traceback
from multiprocessing import cpu_count
from django.utils import timezone
from django.db import transaction

from .models import ServerProblemStatus, Server
from eoj3.settings import TESTDATA_DIR
from problem.models import Problem
from contest.tasks import update_problem_and_participant
from submission.models import Submission, SubmissionStatus
from utils.url_formatter import upload_linker, judge_linker


_WORKER_THREAD_NUM = 0
_WORKER_QUEUE = queue.Queue()
_CONCURRENCY = cpu_count()


class Dispatcher:

    def __init__(self, submission_id):
        # The problem and submission are not bound to be the latest one, therefore
        # each time they are updated, remember: ALWAYS REDO THE QUERY AND CHECK TIME
        self.submission_id = submission_id
        # Get, never used...
        self.submission = Submission.objects.get(pk=submission_id)
        self.problem_id = self.submission.problem_id
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
            file_path = os.path.join(TESTDATA_DIR, str(self.problem_id) + '.zip')
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
        accept_increment = 0
        with transaction.atomic():
            submission = Submission.objects.select_for_update().get(pk=self.submission_id)
            # if submission.judge_start_time > self.submission.judge_start_time:
            #     print('There has been a newer judge')
            #     return
            prev_status = submission.status

            problem = Problem.objects.select_for_update().get(pk=self.problem_id)
            if prev_status != SubmissionStatus.ACCEPTED \
                    and response['verdict'] == SubmissionStatus.ACCEPTED:
                accept_increment = 1
            elif prev_status == SubmissionStatus.ACCEPTED \
                    and response['verdict'] != SubmissionStatus.ACCEPTED:
                accept_increment = -1

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

            problem.add_accept(accept_increment)
            problem.save(update_fields=['total_accept_number'])

        if submission.contest is not None:
            update_problem_and_participant(submission.contest_id, self.problem_id, submission.author_id, accept_increment)

    def dispatch(self):
        # Attempt: 3 times
        for attempt in range(3):
            try:
                if not self.get_server():
                    raise SystemError('No server available.')
                if not self.update_data_for_server():
                    raise SystemError('Data upload failed.')

                with transaction.atomic():
                    self.submission = Submission.objects.select_for_update().get(pk=self.submission_id)
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
            self.submission = Submission.objects.select_for_update().get(pk=self.submission_id)
            self.submission.status = SubmissionStatus.SYSTEM_ERROR
            self.submission.status_percent = 0
            self.submission.status_detail = ''
            self.submission.save()
        return False


class DispatcherThread(threading.Thread):

    def __init__(self, submission_id):
        super().__init__()
        self.submission_id = submission_id

    def run(self):
        global _WORKER_THREAD_NUM, _WORKER_QUEUE
        _WORKER_QUEUE.put(self.submission_id)

        if _WORKER_THREAD_NUM <= Server.objects.count() * _CONCURRENCY:
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


def submit_code(submission, author, problem_pk):
    with transaction.atomic():
        submission.problem = Problem.objects.select_for_update().get(pk=problem_pk)
        submission.author = author
        submission.code_length = len(submission.code)
        submission.save()

        submission.problem.add_submit()
        submission.problem.save()

    DispatcherThread(submission.pk).start()


def submit_code_for_contest(submission, author, problem_identifier, contest):
    """
    :param submission: submission with lang and code
    :param author: submission do not have author yet
    :param problem_identifier: submission do not have a problem yet
    :param contest: submission even do not have a contest
    """
    with transaction.atomic():
        contest_problem = contest.contestproblem_set.select_for_update().get(identifier=problem_identifier)
        submission.problem = Problem.objects.select_for_update().get(pk=contest_problem.problem_id)

        submission.contest = contest
        submission.author = author
        submission.code_length = len(submission.code)
        submission.save()

        contest_problem.add_submit()
        contest_problem.save()

        submission.problem.add_submit()
        submission.problem.save()

    DispatcherThread(submission.pk).start()


def send_rejudge(submission_id):
    accept_increment, problem_id, author_id, contest_id = 0, 0, 0, 0

    with transaction.atomic():
        submission = Submission.objects.select_for_update().get(pk=submission_id)
        if submission.status == SubmissionStatus.ACCEPTED:
            accept_increment = -1
        submission.status = SubmissionStatus.WAITING
        submission.save()
        problem_id, author_id, contest_id = submission.problem_id, submission.author_id, submission.contest_id

        problem = Problem.objects.select_for_update().get(pk=problem_id)
        problem.add_accept(accept_increment)
        problem.save(update_fields=['total_accept_number'])

    if contest_id:
        update_problem_and_participant(contest_id, problem_id, author_id, accept_increment)

    DispatcherThread(submission_id).start()


class ProblemRejudgeThread(threading.Thread):

    def __init__(self, submissions):
        super().__init__()
        self.submissions = submissions

    def run(self):
        for sub in self.submissions:
            send_rejudge(sub)
