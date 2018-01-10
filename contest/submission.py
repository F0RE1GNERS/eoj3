import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, reverse, HttpResponse
from django.views.generic import View, TemplateView
from ipware.ip import get_ip

from account.permissions import is_volunteer
from contest.statistics import invalidate_contest_participant
from problem.tasks import create_submission
from problem.views import StatusList
from submission.models import Submission, SubmissionStatus
from submission.views import render_submission, render_submission_report
from utils.language import LANG_CHOICE
from utils.permission import get_permission_for_submission
from utils.permission import is_contest_manager, is_case_download_available
from .models import ContestProblem
from .tasks import judge_submission_on_contest
from .views import BaseContestMixin


class ContestSubmit(BaseContestMixin, TemplateView):
    template_name = 'contest/submit.jinja2'

    def test_func(self):
        return super(ContestSubmit, self).test_func() and self.user.is_authenticated

    def get_context_data(self, **kwargs):
        data = super(ContestSubmit, self).get_context_data(**kwargs)
        data['lang_choices'] = list(filter(lambda k: k[0] in self.contest.supported_language_list, LANG_CHOICE))
        data['default_problem'] = self.request.GET.get('problem', '')
        return data

    def post(self, request, cid):
        try:
            if self.contest.status != 0:
                raise ValueError("Contest is not running.")
            lang = request.POST.get('lang', '')
            if lang not in self.contest.supported_language_list:
                raise ValueError("Invalid language.")
            try:
                problem = self.contest.contestproblem_set.get(identifier=request.POST.get('problem', '')).problem_id
            except ContestProblem.DoesNotExist:
                raise ValueError("Invalid problem.")
            submission = create_submission(problem, self.user, request.POST.get('code', ''), lang,
                                           contest=self.contest, ip=get_ip(request))
            contest_participant, _ = self.contest.contestparticipant_set.get_or_create(user=self.user)
            if contest_participant.is_disabled:
                raise ValueError("You have quitted the contest.")
            judge_submission_on_contest(submission)
            return JsonResponse({"url": reverse('contest:submission_api',
                                                kwargs={'cid': self.contest.id, 'sid': submission.id})})
        except Exception as e:
            return HttpResponseBadRequest(str(e).encode())


class ContestSubmissionClaim(BaseContestMixin, View):
    def test_func(self):
        return self.contest.always_running and super().test_func() and self.user.is_authenticated

    def prepare_submissions(self):
        contest_already_accept = set()
        self.submissions = []
        for submission in self.contest.submission_set.filter(status=SubmissionStatus.ACCEPTED, author=self.user).\
                defer("code", "status_detail", "status_message"):
            contest_already_accept.add(submission.problem_id)
        aiming_problems = list(filter(lambda x: x not in contest_already_accept,
                                      self.contest.contestproblem_set.values_list("problem_id", flat=True)))
        for submission in self.user.submission_set.filter(
                problem_id__in=aiming_problems, status=SubmissionStatus.ACCEPTED).all():
            if submission.problem_id not in contest_already_accept and submission.lang in self.contest.allowed_lang:
                self.submissions.append(submission)
                contest_already_accept.add(submission.problem_id)

    def post(self, request, cid):
        contest_participant, _ = self.contest.contestparticipant_set.get_or_create(user=self.user)
        self.prepare_submissions()
        if len(self.submissions) > 0:
            for submission in self.submissions:
                submission.pk = None
                submission.contest = self.contest
            Submission.objects.bulk_create(self.submissions)
            invalidate_contest_participant(self.contest, self.user.pk)
            messages.add_message(request, messages.SUCCESS, "%d submissions successfully migrated." % len(self.submissions))
        return HttpResponse()


class ContestSubmissionAPI(BaseContestMixin, View):
    def get(self, request, cid, sid):
        if not request.user.is_authenticated:
            raise PermissionDenied
        submission = get_object_or_404(Submission, contest_id=cid, author=request.user, pk=sid)
        if self.contest.case_public and submission.is_judged and \
                is_case_download_available(self.request.user, submission.problem_id, submission.contest_id):
            submission.allow_case_download = True
        return HttpResponse(
            render_submission(submission, permission=get_permission_for_submission(request.user, submission),
                              hide_problem=True))


class ContestSubmissionView(BaseContestMixin, TemplateView):
    template_name = 'submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestSubmissionView, self).get_context_data(**kwargs)
        data['submission'] = submission = get_object_or_404(Submission, contest_id=self.kwargs.get('cid'),
                                                            pk=self.kwargs.get('sid'))
        submission.contest_problem = self.contest.get_contest_problem(submission.problem_id)
        if submission.author == self.request.user and self.contest.case_public and submission.is_judged and \
                is_case_download_available(self.request.user, submission.problem_id, submission.contest_id):
            submission.allow_case_download = True
        authorized = False
        if self.request.user.is_authenticated:  # Check author or managers (no share)
            if is_contest_manager(self.request.user,
                                  self.contest) or self.request.user == submission.author:
                authorized = True
            if not authorized and self.contest.allow_code_share > 0:  # start to share
                if self.contest.status > 0 and self.contest.allow_code_share >= 2:
                    authorized = True
                if self.request.user.submission_set.filter(problem_id=submission.problem_id,
                                                           status=SubmissionStatus.ACCEPTED).exists() and (
                                self.contest.status > 0 or self.contest.allow_code_share >= 3):
                    authorized = True
        if authorized:
            permission = get_permission_for_submission(self.request.user, submission, special_permission=True)
            # it is already authorized thus requires special permission to open it
            data['submission_block'] = render_submission(submission,
                                                         permission=permission,
                                                         show_percent=(self.contest.scoring_method == 'oi'))
            if permission == 2 or (self.request.user == submission.author and submission.report_paid):
                data['report_block'] = render_submission_report(submission.pk)
            else:
                data['report_block'] = ''
        else:
            raise PermissionDenied
        return data


class ContestMyPastSubmissions(BaseContestMixin, TemplateView):
    template_name = 'components/past_submissions.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestMyPastSubmissions, self).get_context_data(**kwargs)
        data['submission_list'] = self.contest.submission_set.only("problem_id", "id", "status", "status_private",
                                                                   "status_private", "create_time", "contest_id",
                                                                   "author_id", "author__username",
                                                                   "author__nickname", "author__magic"). \
                                      filter(author_id=self.request.user.pk)[:20]
        self.contest.add_contest_problem_to_submissions(data['submission_list'])
        data['view_more'] = True
        return data


class ContestStatus(BaseContestMixin, StatusList):
    template_name = 'contest/status.jinja2'
    contest_submission_visible = True

    def get_selected_from(self):
        return self.contest.submission_set.all()

    def reinterpret_problem_identifier(self, value):
        return self.contest.contestproblem_set.get(identifier=value).problem_id

    def get_context_data(self, **kwargs):
        data = super(ContestStatus, self).get_context_data(**kwargs)
        self.contest.add_contest_problem_to_submissions(data['submission_list'])
        return data


class ContestStatusForAll(ContestStatus):
    def test_func(self):
        if self.privileged:
            return True
        if self.contest.standings_disabled:
            return False
        return super().test_func()


class ContestPenaltyDetail(ContestStatus):
    template_name = 'contest/standings_penalty_detail.jinja2'

    def get_context_data(self, **kwargs):
        if 'user' not in self.request.GET or 'problem' not in self.request.GET:
            raise PermissionDenied
        return super().get_context_data(**kwargs)


class ContestMyStatus(ContestStatus):
    template_name = 'contest/my_status.jinja2'

    def test_func(self):
        return super().test_func() and self.user.is_authenticated

    def get_selected_from(self):
        if not self.user.is_authenticated:
            raise PermissionDenied
        if not self.contest.always_running:
            return self.contest.submission_set.filter(author=self.user).all()
        else:
            return self.user.submission_set.filter(
                problem_id__in=self.contest.contestproblem_set.values_list("problem_id", flat=True)).all()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data.update(hide_users=True)
        return data


class ContestBalloon(BaseContestMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse()


def balloon_switch(request, pk):
    if not is_volunteer(request.user):
        raise PermissionDenied("You don't have the access.")
    with transaction.atomic():
        submission = Submission.objects.select_for_update().get(pk=pk)
        submission.addon_info = True
        submission.save(update_fields=['addon_info'])
    return HttpResponse(json.dumps({"result": "success"}))
