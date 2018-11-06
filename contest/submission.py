import json

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, reverse, HttpResponse, redirect
from django.views.generic import ListView
from django.views.generic import View, TemplateView
from django_q.tasks import async_task
from ipware.ip import get_ip

from contest.statistics import invalidate_contest_participant
from problem.statistics import invalidate_problem
from problem.tasks import create_submission
from problem.views import StatusList
from submission.models import Submission, SubmissionStatus
from submission.views import render_submission, render_submission_report
from utils.language import LANG_CHOICE
from utils.permission import get_permission_for_submission
from utils.permission import is_contest_manager, is_case_download_available
from .models import ContestProblem, ContestParticipant
from .tasks import judge_submission_on_contest
from .views import BaseContestMixin


class ContestSubmit(BaseContestMixin, View):
    def post(self, request, cid, pid):
        try:
            if self.contest.status < 0 and not self.privileged:  # pending contest
                raise ValueError("比赛尚未开始。")
            if self.contest.run_tests_during_contest != 'all' and self.contest.status != 0 and \
                    not self.contest.system_tested and not self.privileged:  # pending result
                raise ValueError("比赛仍在等待系统测试。")
            lang = request.POST.get('lang', '')
            if lang not in self.contest.supported_language_list:
                raise ValueError("语言无效。")
            try:
                problem = self.contest.contestproblem_set.get(identifier=pid).problem_id
            except ContestProblem.DoesNotExist:
                raise ValueError("题目无效。")

            code = request.POST.get('code', '')
            if self.contest.status < 0:
                submission = create_submission(problem, self.user, code, lang, ip=get_ip(request))
            elif self.contest.status > 0 and self.contest.contest_type == 1:
                raise ValueError("不在提交时间内。")
            else:
                submission = create_submission(problem, self.user, code, lang,
                                               contest=self.contest, ip=get_ip(request))
                contest_participant, created = self.contest.contestparticipant_set.get_or_create(user=self.user)
                if created and (self.contest.status != 0 or self.contest.access_level == 30):
                    contest_participant.star = True
                    contest_participant.save(update_fields=['star'])
                if contest_participant.is_disabled:
                    raise ValueError("你已退出比赛。")
            response = {"url": reverse('contest:submission_api',
                                       kwargs={'cid': self.contest.id, 'sid': submission.id})}
            async_task(judge_submission_on_contest, submission, contest=self.contest)
            return JsonResponse(response)
        except Exception as e:
            return HttpResponseBadRequest(str(e).encode())


class ContestSubmissionClaim(BaseContestMixin, View):
    def test_func(self):
        return self.contest.contest_type == 1 and super().test_func() and self.user.is_authenticated

    def prepare_submissions(self):
        contest_already_accept = set()
        self.submissions = []
        self.problem_id_list = list(self.contest.contestproblem_set.values_list("problem_id", flat=True))
        for submission in self.contest.submission_set.filter(status=SubmissionStatus.ACCEPTED, author=self.user).\
                defer("code", "status_detail", "status_message"):
            contest_already_accept.add(submission.problem_id)
        aiming_problems = list(filter(lambda x: x not in contest_already_accept, self.problem_id_list))
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
            invalidate_problem(self.problem_id_list, self.contest.pk)
            messages.add_message(request, messages.SUCCESS, "%d 份提交已经成功迁移。" % len(self.submissions))
        return HttpResponse()


def get_contest_submission(submission_id, contest_id, author_id=None):
    if author_id is None:
        submission = get_object_or_404(Submission, pk=submission_id)
    else:
        submission = get_object_or_404(Submission, pk=submission_id, author_id=author_id)
    if submission.contest_id != contest_id and \
            not ContestProblem.objects.filter(contest_id=contest_id, problem_id=submission.problem_id).exists():
        raise Http404
    return submission


class ContestSubmissionAPI(BaseContestMixin, View):
    def get(self, request, cid, sid):
        if not request.user.is_authenticated:
            raise PermissionDenied
        submission = get_contest_submission(sid, cid, author_id=request.user.pk)
        if self.contest.case_public and submission.is_judged and \
                is_case_download_available(self.request.user, submission.problem_id, submission.contest_id):
            submission.allow_case_download = True
        return HttpResponse(
            render_submission(submission, permission=get_permission_for_submission(request.user, submission),
                              hide_problem=True, rejudge_available=False))


class ContestSubmissionView(BaseContestMixin, TemplateView):
    template_name = 'submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestSubmissionView, self).get_context_data(**kwargs)
        data['submission'] = submission = get_contest_submission(self.kwargs.get('sid'), self.kwargs.get('cid'))
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
        if self.contest.status > 0 and self.request.user.is_authenticated and self.request.user.has_coach_access():
            authorized = True
        if authorized:
            permission = get_permission_for_submission(self.request.user, submission, special_permission=True)
            # it is already authorized thus requires special permission to open it
            data['submission_block'] = render_submission(submission,
                                                         permission=permission,
                                                         show_percent=data['show_percent'])
            if permission == 2 or (self.request.user == submission.author and submission.report_paid) or \
                    (self.contest.status > 0 and self.request.user.has_coach_access()) or self.contest.case_public >= 2:
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
        try:
            problem = self.contest.contestproblem_set.get(identifier=kwargs.get('pid')).problem_id
            data['submission_list'] = Submission.objects.defer("code", "status_message", "status_detail"). \
                                          filter(author_id=self.request.user.pk, problem_id=problem)[:15]
            self.contest.add_contest_problem_to_submissions(data['submission_list'])
            for submission in data['submission_list']:
                if submission.contest_id is None or submission.contest_id != self.contest.pk:
                    submission.unofficial = True
                    submission.contest_id = self.contest.pk
        except ContestProblem.DoesNotExist:
            data['submission_list'] = []
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
        for submission in data['submission_list']:
            if submission.contest_id is None or submission.contest_id != self.contest.pk:
                submission.unofficial = True
                submission.contest_id = self.contest.pk
        return data


class ContestStatusForAll(ContestStatus):
    def test_func(self):
        if self.privileged:
            return True
        if self.contest.common_status_access_level < 0:
            return False
        return super().test_func()


class ContestPenaltyDetail(ContestStatus):
    template_name = 'contest/standings_penalty_detail.jinja2'
    paginate_by = None

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
        if not self.contest.contest_type == 1 and self.contest.status == 0 and not self.privileged:
            return self.contest.submission_set.filter(author=self.user).all()
        else:
            return self.user.submission_set.filter(
                problem_id__in=self.contest.contestproblem_set.values_list("problem_id", flat=True)).all()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data.update(hide_users=True)
        return data


BALLOON_CACHE_NAME = "balloon%d|%d|%d"


class ContestBalloon(BaseContestMixin, ListView):
    paginate_by = None
    context_object_name = "balloon_list"
    template_name = 'contest/balloon.jinja2'

    def test_func(self):
        return super().test_func() and self.volunteer

    def get_queryset(self):
        contest_participants = {user.user_id: user.comment for user in
                                ContestParticipant.objects.filter(contest=self.contest).select_related('user',
                                                                                                       'contest').
                                    all()}
        qs = self.contest.submission_set.filter(status=SubmissionStatus.ACCEPTED).\
            defer("code", "status_message", "status_detail").all()
        available = set(cache.get_many(list(map(lambda x: BALLOON_CACHE_NAME % (x.contest_id, x.author_id, x.problem_id), qs))).keys())
        self.contest.add_contest_problem_to_submissions(qs)
        for submission in qs:
            submission.username = contest_participants.get(submission.author_id, "INVALID")
            if BALLOON_CACHE_NAME % (submission.contest_id, submission.author_id, submission.problem_id) in available:
                submission.ok = True
        return qs


class ContestBalloonClaim(BaseContestMixin, TemplateView):
    template_name = 'contest/balloon_detail.jinja2'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        try:
            data['submission'] = submission = self.contest.submission_set.get(pk=self.kwargs["pk"])
            self.contest.add_contest_problem_to_submissions([submission])
            submission.username = ContestParticipant.objects.get(user_id=submission.author_id, contest=self.contest).comment
            data['cache_name'] = BALLOON_CACHE_NAME % (submission.contest_id, submission.author_id, submission.problem_id)
            if cache.get(data['cache_name']):
                submission.ok = True
            else:
                submission.ok = False
            return data
        except:
            raise PermissionDenied

    def post(self, request, *args, **kwargs):
        data = self.get_context_data()
        if data["submission"].ok:
            messages.error(request, "气球已被认领。")
            return redirect(reverse('contest:balloon', kwargs={'cid': self.contest.pk}))
        cache.set(data['cache_name'], True, 86400 * 14)
        return redirect(self.request.path)


class ContestBalloonCancel(BaseContestMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            submission = self.contest.submission_set.get(pk=self.kwargs["pk"])
            cache.delete(BALLOON_CACHE_NAME % (submission.contest_id, submission.author_id, submission.problem_id))
            return redirect(reverse('contest:balloon', kwargs={'cid': self.contest.pk}))
        except:
            raise PermissionDenied
