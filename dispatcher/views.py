from django.shortcuts import render
import requests
import os
import threading

from .models import ServerProblemStatus, Server
from problem.models import Problem
from submission.models import Submission
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
            return
        try:
            file_path = os.path.join(TESTDATA_DIR, str(self.problem.pk) + '.zip')
            with open(file_path, 'rb') as f:
                response = requests.post(upload_linker(self.server.ip, self.server.port, self.problem.pk),
                                         data=f.read(), auth=('token', self.server.token)).json()
                print(response)
                if response['status'] != 'received':
                    raise ConnectionError('Remote server rejected the request.')
                self.status.testdata_hash = self.problem.testdata_hash
        except Exception as e:
            print('Something wrong during update:')
            print(e)

    def dispatch(self):
        self.update_data_for_server()
        self.server.save()
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
        try:
            response = requests.post(judge_linker(self.server.ip, self.server.port),
                                     json=request, auth=('token', self.server.token)).json()
            print(response)
        except Exception as e:
            pass


class DispatcherThread(threading.Thread):

    def __init__(self, problem_id, submission):
        super().__init__()
        self.problem_id = problem_id
        self.submission = submission

    def run(self):
        Dispatcher(self.problem_id, self.submission).dispatch()


def test():
    sub = Submission(lang='cpp', code='int main() { return 0; }')
    Dispatcher(1, 'ccc').update_data_for_server()