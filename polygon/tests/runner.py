import os
import shutil
from datetime import datetime

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import TestCase
from django.urls import reverse
from os import path

from account.models import User
from polygon.models import Case, Revision, Asset, Statement, Program
from polygon.problem2.runner import Runner
from polygon.problem2.runner.exception import CompileError
from polygon.problem2.views.case import CaseManagementTools
from problem.models import Problem

BASE_LOCATION = path.dirname(path.abspath(__file__))


class RunnerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="something@user.com", username="myusername", is_staff=True,
                                        polygon_enabled=True)
        self.user.set_password("password")
        self.user.save()
        shutil.rmtree(os.path.join(settings.UPLOAD_DIR, "1"), ignore_errors=True)

        self.client.login(username='myusername', password='password')
        self.assertContains(self.client.post(reverse('polygon:problem_create_2')), '')
        self.assertEqual(1, Problem.objects.all().count())
        self.problem = Problem.objects.all().first()

        self.client.post(reverse('polygon:revision_create', kwargs={'pk': self.problem.id}))
        self.assertEqual(1, self.problem.revisions.all().count())
        self.revision = self.problem.revisions.all().first()

    def test_compile(self):
        program = Program(name="hello",
                          lang="cpp",
                          code="int main() { return 0; }",
                          tag="solution_main_correct")
        runner = Runner(program)
        with self.assertRaises(CompileError):
            program = Program(name="hello",
                              lang="cpp",
                              code="int main() { return 0 }",
                              tag="solution_main_correct")
            runner = Runner(program)
        program = Program(name="hello",
                          lang="java",
                          code="class Main { }",
                          tag="solution_main_correct")
        runner = Runner(program)

    def test_run(self):
        code = """a, b = map(int, input().split())
print(a + b)"""
        code_time_limit = """int main() { int p = 999999999; int a = 0; while (1) { a++; } }"""
        program = Program(name="hello",
                          lang="python",
                          code=code,
                          tag="solution_main_correct")
        runner = Runner(program)
        self.assertEqual(runner.workspace, os.getcwd())
        with open("1.in", "w") as f:
            f.write("1 2")
        result = runner.run(stdin="1.in", stdout="1.out", stderr="1.err")
        with open("1.out", "r") as f:
            self.assertEqual(f.read().strip(), "3")
        print(result)
        program = Program(name="hello2",
                          lang="cpp",
                          code=code_time_limit,
                          tag="solution_main_correct")
        runner = Runner(program)
        self.assertEqual(runner.workspace, os.getcwd())
        result = runner.run(stderr="runtime.log")
        print(result)
        self.assertEqual(result["verdict"], "TIME_LIMIT")

    def test_run_all_cases(self):
        self.revision.programs.create(name="gen",
                                      lang="python",
                                      code="""from random import randint
print("%d %d" % (randint(1, 10), randint(1, 10)))""",
                                      tag="generator",
                                      create_time=datetime.now())
        CaseManagementTools.generate_cases(self.revision, ["gen 1 2" for i in range(10)])
        for i in self.revision.cases.all():
            print(i.input_preview)
