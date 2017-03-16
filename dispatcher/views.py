from django.shortcuts import render
from django.utils import timezone
import requests
import os
import threading
import json

from .models import ServerProblemStatus, Server
from problem.models import Problem
from submission.models import Submission, SubmissionStatus
from eoj3.settings import TESTDATA_DIR
from utils.url_formatter import upload_linker, judge_linker


class Dispatcher:

    def __init__(self, problem_id, submission):
        self.problem = Problem.objects.get(pk=problem_id)
        self.server = Server.objects.get()
        self.submission = submission
        print(self.problem, self.server)

    def is_latest_data_for_server(self):
        result = ServerProblemStatus.objects.filter(problem=self.problem, server=self.server)
        if len(result) == 0:
            self.status = ServerProblemStatus(problem=self.problem,
                                              server=self.server,
                                              testdata_hash='')
        else:
            self.status = result[0]
        if self.status.testdata_hash != self.problem.testdata_hash:
            return False
        return True

    def update_data_for_server(self):
        if self.is_latest_data_for_server():
            return True
        try:
            file_path = os.path.join(TESTDATA_DIR, str(self.problem.pk) + '.zip')
            with open(file_path, 'rb') as f:
                response = requests.post(upload_linker(self.server.ip, self.server.port, self.problem.pk),
                                         data=f.read(), auth=('token', self.server.token)).json()
                print(response)
                if response['status'] != 'received':
                    raise ConnectionError('Remote server rejected the request.')
                self.status.testdata_hash = self.problem.testdata_hash
                return True
        except FileNotFoundError:
            print('Data file not found. Why?')
            return True
        except Exception as e:
            print('Something wrong during update:')
            print(e)
            return False

    def dispatch(self):
        try:
            self.update_data_for_server()
            self.server.save()
            self.submission.judge_start_time = timezone.now()
            self.submission.status = SubmissionStatus.JUDGING
            self.submission.save()
            request = {
                "id": self.submission.pk,
                "lang": self.submission.lang,
                "code": self.submission.code,
                "settings": {
                    "max_time": self.problem.time_limit,
                    "max_sum_time": self.problem.sum_time_limit,
                    "max_memory": self.problem.memory_limit,
                    "problem_id": self.problem.pk
                },
                "judge": self.problem.judge
            }
            # Request: wait for one hour
            response = requests.post(judge_linker(self.server.ip, self.server.port),
                                     json=request, auth=('token', self.server.token),
                                     timeout=3600).json()
            # If presented multiple judge responses at the same time, unexpected results will happen.
            if response['status'] != 'received':
                raise ConnectionError('Remote server rejected the request.')
            print(response)
            self.submission.judge_end_time = timezone.now()
            self.submission.status = response['verdict']
            if self.submission.status == SubmissionStatus.COMPILE_ERROR:
                self.submission.status_detail = response['message']
            else:
                self.submission.status_detail = json.dumps(response['detail'])
                self.submission.status_time = response['time']
                self.submission.status_memory = response['memory']
            self.submission.save()
            return True
        except Exception as e:
            print('Something wrong during dispatch:')
            print(e)
            return False


class DispatcherThread(threading.Thread):

    def __init__(self, problem_id, submission):
        super().__init__()
        self.problem_id = problem_id
        self.submission = submission

    def run(self):
        server_count = len(Server.objects.all())
        count = 0
        while True:
            if count > server_count * 2:
                self.submission.status = SubmissionStatus.SYSTEM_ERROR
                self.submission.save()
                break
            if Dispatcher(self.problem_id, self.submission).dispatch():
                break
            count += 1
