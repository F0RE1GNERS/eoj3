import os

import subprocess
import traceback

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django_q.tasks import async_task

from contest.models import Contest, ContestProblemPlag
from polygon.contest.views import PolygonContestMixin
from submission.util import SubmissionStatus
from utils import random_string


class JPlagManager():
    def __init__(self, plag: ContestProblemPlag):
        self.plag = plag
        self.contest = plag.contest
        self.workspace = os.path.join(settings.GENERATE_DIR, "jplag", str(self.contest.pk), plag.fingerprint)
        self.code_dir = os.path.join(self.workspace, "code")
        self.result_dir = os.path.join(self.workspace, "result")
        os.makedirs(self.workspace, exist_ok=True)
        os.makedirs(self.code_dir, exist_ok=True)
        os.makedirs(self.result_dir, exist_ok=True)

    def code_ready(self):
        problem_id = self.contest.contestproblem_set.get(identifier=self.plag.identifier).problem_id
        for s in self.contest.submission_set.filter(contest_time__isnull=False, status=SubmissionStatus.ACCEPTED,
                                                    problem_id=problem_id):
            with open(os.path.join(self.code_dir, "%d_%d.cpp" % (s.pk, s.author_id)), "w", encoding="utf-8") as f:
                f.write(s.code)

    def run(self):
        with open(os.path.join(self.result_dir, "stdout"), "w") as stdout_file, \
                open(os.path.join(self.result_dir, "stderr"), "w") as stderr_file:
            retcode = subprocess.call(
                ["java", "-jar", os.path.join(settings.BASE_DIR, "polygon/assets/jplag-2.11.9_SNAPSHOT.jar"),
                 "-vq", "-m", str(self.plag.keep_match), "-l", self.plag.language,
                 "-r", self.result_dir, self.code_dir], timeout=300,
                stdout=stdout_file, stderr=stderr_file)
            if retcode:
                self.plag.status = 1
            else:
                self.plag.status = 0
            self.plag.save()


def start_jplag(plags):
    for plag in plags:
        manager = JPlagManager(plag)
        try:
            manager.code_ready()
            manager.run()
        except Exception as e:
            plag.status = 1
            with open(os.path.join(manager.result_dir, "stderr"), "a", encoding="utf-8") as f:
                print(traceback.format_exc(), file=f)
            plag.save()


class JPlagHistoryView(PolygonContestMixin, ListView):
    template_name = 'contest/anticheat.jinja2'
    context_object_name = 'plag_list'

    def get_queryset(self):
        return self.contest.contestproblemplag_set.all().order_by("-create_time")


class JPlagCreateView(PolygonContestMixin, View):

    def post(self, request, *args, **kwargs):
        keep = request.POST.get("answer", 1000)
        if not keep:
            keep = 1000
        plags = []
        for problem in self.contest.contest_problem_list:
            plags.append(ContestProblemPlag.objects.create(contest=self.contest, fingerprint=random_string(64),
                                                           identifier=problem.identifier, keep_match=keep, status=-1))
        async_task(start_jplag, plags)
        return redirect(reverse("polygon:contest_plag", kwargs={"pk": self.contest.pk}))
