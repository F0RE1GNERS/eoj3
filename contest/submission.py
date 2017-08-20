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
from .views import BaseContestMixin, time_formatter
from submission.models import Submission, SubmissionStatus
from submission.views import render_submission
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
        problem = self.contest.contestproblem_set.get(identifier=request.POST['problem']).problem_id
        submission = create_submission(problem, self.user, request.POST['code'], request.POST['lang'],
                                       contest=self.contest)
        if self.contest.run_tests_during_contest != 'none':
            judge_submission_on_problem(submission, callback=None, case=self.contest.run_tests_during_contest,
                                        status_private=self.contest.is_frozen)
        else:
            submission.status = submission.status_private = SubmissionStatus.SUBMITTED
            submission.save(update_fields=['status', 'status_private'])
        return HttpResponse(json.dumps({"url": reverse('contest:submission_api',
                                                       kwargs={'cid': self.contest.id, 'sid': submission.id})}))


class ContestSubmissionAPI(BaseContestMixin, TemplateView):

    template_name = 'components/single_submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestSubmissionAPI, self).get_context_data(**kwargs)
        data['submission'] = Submission.objects.get(contest_id=self.kwargs.get('cid'),
                                                    author=self.request.user,
                                                    pk=self.kwargs.get('sid'))
        data['hide_problem'] = True
        return data


class ContestSubmissionView(BaseContestMixin, TemplateView):

    template_name = 'submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestSubmissionView, self).get_context_data(**kwargs)
        data['submission'] = submission = Submission.objects.get(contest_id=self.kwargs.get('cid'),
                                                                 pk=self.kwargs.get('sid'))
        submission.contest_problem = self.contest.get_contest_problem(submission.problem_id)
        submission_block = render_submission(submission)
        data['submission_block'] = submission_block
        return data



class ContestMySubmission(BaseContestMixin, TemplateView):

    template_name = 'components/past_submissions.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestMySubmission, self).get_context_data(**kwargs)
        data['submission_list'] = self.contest.submission_set.only("problem_id", "id", "status",
                                                                   "create_time", "contest_id",
                                                                   "author_id", "author__username",
                                                                   "author__magic"). \
            filter(author_id=self.request.user.pk)
        self.contest.add_contest_problem_to_submissions(data['submission_list'])
        return data


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
        self.contest.add_contest_problem_to_submissions(data['submission_list'])
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
            submission.contest_problem = self.contest.get(submission.problem_id)
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
