import requests
import os
import threading
import json
from django.utils import timezone
from django.db import transaction

from .models import ServerProblemStatus, Server
from eoj3.settings import TESTDATA_DIR
from account.models import User
from problem.models import Problem
from contest.tasks import update_problem_and_participant
from submission.models import Submission, SubmissionStatus
from utils.url_formatter import upload_linker, judge_linker


class Dispatcher:

    def __init__(self, problem_id, submission_id):
        # The problem and submission are not bound to be the latest one, therefore
        # each time they are updated, remember: ALWAYS REDO THE QUERY AND CHECK TIME
        self.problem_id = problem_id
        self.submission_id = submission_id
        # Get, never used...
        self.submission = Submission.objects.get(pk=submission_id)

        try:
            # Get a server
            with transaction.atomic():
                servers = Server.objects.select_for_update().all()
                if servers.exists():
                    server = servers.first()
                    server.last_seen_time = timezone.now()
                    self.server_id = server.pk
                    server.save()
                else:
                    raise SystemError
        except SystemError:
            # If the program goes here, there is no server available
            with transaction.atomic():
                submission = Submission.objects.select_for_update().get(pk=self.submission_id)
                submission.status = SubmissionStatus.SYSTEM_ERROR
                submission.save()

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
            with transaction.atomic():
                server_status = ServerProblemStatus.objects.select_for_update().get(problem__pk=self.problem_id,
                                                                                    server__pk=self.server_id)
                server = Server.objects.get(pk=self.server_id)
                problem_hash = Problem.objects.get(pk=self.problem_id).testdata_hash
                with open(file_path, 'rb') as f:
                    response = requests.post(upload_linker(server.ip, server.port, self.problem_id),
                                             data=f.read(), auth=('token', server.token)).json()
                    if response['status'] != 'received':
                        raise ConnectionError('Remote server rejected the request.')
                    server_status.testdata_hash = problem_hash
                    server_status.save(update_fields=["testdata_hash"])
            return True
        except FileNotFoundError:
            print('Data file not found. Why?')
            return False
        except Exception as e:
            print('Something wrong during update:')
            print(e)
            return False

    def update_submission_and_problem(self, response):
        submission = Submission.objects.select_for_update().get(pk=self.submission_id)
        if submission.judge_start_time > self.submission.judge_start_time:
            raise SystemError('There has been a newer judge')
        prev_status = submission.status

        accept_increment = 0
        problem = Problem.objects.select_for_update().get(pk=self.problem_id)
        if prev_status != SubmissionStatus.ACCEPTED \
                and response['verdict'] == SubmissionStatus.ACCEPTED:
            accept_increment = 1
        elif prev_status == SubmissionStatus.ACCEPTED \
                and response['verdict'] != SubmissionStatus.ACCEPTED:
            accept_increment = -1

        with transaction.atomic():
            submission.status = response['verdict']
            submission.judge_end_time = timezone.now()
            if submission.status == SubmissionStatus.COMPILE_ERROR:
                submission.status_detail = response['message']
            else:
                submission.status_detail = json.dumps(response['detail'])
                submission.status_time = response['time']
                submission.status_memory = response['memory']
                # Get percent (just for OI)
                accept_case_number = len([x for x in response['detail'] if x['verdict'] == SubmissionStatus.ACCEPTED])
                if response['detail']:
                    submission.status_percent = int(accept_case_number / len(response['detail']) * 100)
            submission.save()

            problem.add_accept(accept_increment)
            problem.save(update_fields=['total_accept_number'])

        if submission.contest is not None:
            user_id = submission.author.pk
            update_problem_and_participant(submission.contest.pk, self.problem_id, user_id, accept_increment)

    def dispatch(self):
        try:
            self.update_data_for_server()

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
            print(response)
            if response['status'] != 'received':
                raise ConnectionError('Remote server rejected the request.')

            self.update_submission_and_problem(response)
            return True
        except Exception as e:
            print('Something wrong during dispatch:')
            print(e)
            return False


class DispatcherThread(threading.Thread):

    def __init__(self, problem_id, submission_id):
        super().__init__()
        self.problem_id = problem_id
        self.submission_id = submission_id

    def run(self):
        Dispatcher(self.problem_id, self.submission_id).dispatch()
