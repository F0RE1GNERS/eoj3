from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse, HttpResponse
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction

from problem.views import StatusList, ProblemPersonalSubmissionAPI
from problem.tasks import create_submission, judge_submission_on_problem
from account.permissions import is_volunteer
from .models import Contest, ContestProblem
from .views import BaseContestMixin, time_formatter, get_contest_problem
from submission.models import Submission, SubmissionStatus
from submission.forms import ContestSubmitForm
from dispatcher.tasks import submit_code_for_contest
from utils.language import LANG_CHOICE

import json


class ContestSubmit(BaseContestMixin, TemplateView):

    template_name = 'contest/submit.jinja2'

    def test_func(self):
        return super(ContestSubmit, self).test_func() and self.user.is_authenticated

    def get_context_data(self, **kwargs):
        data = super(ContestSubmit, self).get_context_data(**kwargs)
        data['lang_choices'] = list(filter(lambda k: k[0] in self.contest.supported_language_list, LANG_CHOICE))
        return data

    def post(self, request, cid):
        if self.contest.status != 0:
            raise PermissionDenied
        if request.POST['lang'] not in self.contest.supported_language_list:
            raise PermissionDenied
        problem = get_contest_problem(self.contest, request.POST['problem'])
        submission = create_submission(problem, self.user, request.POST['code'], request.POST['lang'], self.contest)
        if self.contest.run_tests_during_contest != 'none':
            judge_submission_on_problem(submission, callback=None, case=self.contest.run_tests_during_contest)
        return HttpResponse()


class ContestMySubmission(BaseContestMixin, View):

    def get(self, request, cid):
        subs = []
        SUB_FIELDS = ["id", "status", "problem_id"]
        for sub in self.contest.submission_set.filter(author=self.user).only("create_time", "author", "status", "problem_id"). \
                order_by("-create_time").all():
            subs.append({k: getattr(sub, k) for k in SUB_FIELDS})
        for sub in subs:
            sub["problem_id"] = get_contest_problem(self.contest, sub["problem_id"]).identifier
        return HttpResponse(json.dumps(subs))


class ContestStatus(BaseContestMixin, StatusList):

    template_name = 'contest/status.jinja2'

    def get_selected_from(self):
        if self.contest.is_frozen:
            return self.contest.submission_set.filter(create_time__lt=self.contest.freeze_time)
        return self.contest.submission_set.all()

    def reinterpret_problem_identifier(self, value):
        return self.contest.contestproblem_set.get(identifier=value).problem_id

    def get_context_data(self, **kwargs):
        data = super(ContestStatus, self).get_context_data(**kwargs)
        find_contest_problem = {k.problem_id: k for k in self.contest.contest_problem_list}
        for submission in data['submission_list']:
            submission.contest_problem = find_contest_problem[submission.problem_id]
        return data


class ContestBalloon(BaseContestMixin, ListView):
    template_name = 'contest/balloon.jinja2'
    paginate_by = 100
    context_object_name = 'submission_list'

    def test_func(self):
        if not self.privileged and not self.volunteer:
            raise PermissionDenied("You don't have the access.")
        return True

    def get_queryset(self):
        queryset = self.contest.submission_set.select_related('author').\
            only('pk', 'contest_id', 'create_time', 'author_id', 'author__username', 'author__nickname',
                 'author__magic', 'problem_id', 'status', 'addon_info').filter(status=SubmissionStatus.ACCEPTED, addon_info=False)
        return queryset.all()

    def get_context_data(self, **kwargs):
        data = super(ContestBalloon, self).get_context_data(**kwargs)
        author_list = set(x.author_id for x in data['submission_list'])
        contest_participants = self.contest.contestparticipant_set.filter(user_id__in=author_list).\
            only("user_id", "comment", "contest_id").all()
        contest_participant_set = dict()
        for participant in contest_participants:
            contest_participant_set[participant.user_id] = participant.comment
        for submission in data['submission_list']:
            submission.comment = contest_participant_set[submission.author_id]
            submission.create_time = time_formatter((submission.create_time - self.contest.start_time).total_seconds())
            submission.contest_problem = get_contest_problem(self.contest, submission.problem_id)
            if type(submission.contest_problem) == ContestProblem:
                submission.contest_problem = submission.contest_problem.identifier
        return data


def balloon_switch(request, pk):
    if not is_volunteer(request.user):
        raise PermissionDenied("You don't have the access.")
    with transaction.atomic():
        submission = Submission.objects.select_for_update().get(pk=pk)
        submission.addon_info = True
        submission.save(update_fields=['addon_info'])
    return HttpResponse(json.dumps({"result": "success"}))
