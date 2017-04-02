from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages

from .models import Contest, ContestProblem, ContestParticipant, ContestInvitation
from .tasks import add_participant_with_invitation
from submission.models import SubmissionStatus
from account.permissions import is_admin_or_root


def time_formatter(seconds):
    return "%d:%.2d:%.2d" % (seconds // 3600,
                             seconds % 3600 // 60,
                             seconds % 60)


def get_contest_problem(contest, problem):
    try:
        return contest.contestproblem_set.get(problem=problem)
    except ContestProblem.DoesNotExist:
        return 'N/A'


class BaseContestMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):
    raise_exception = True  # TODO show permission denied message

    def test_func(self):
        user = self.request.user
        contest = Contest.objects.get(pk=self.kwargs.get('cid'))
        if is_admin_or_root(user):
            return True
        if not contest.visible:
            self.permission_denied_message = 'Contest is not visible.'
            return False
        if contest.start_time > timezone.now():
            self.permission_denied_message = "Contest hasn't started."
            return False
        if contest.public:
            return True         # Public does not need user verification
        if user.is_authenticated and ContestParticipant.objects.filter(contest=contest, user=user).exists():
            return True
        else:
            self.permission_denied_message = "Did you forget to register for the contest?"
            return False

    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])
        data['contest'] = contest
        data['contest_status'] = contest.get_status()
        data['current_time'] = timezone.now()

        if data['contest_status'] == 'ended':
            data['progress'] = 100
        elif data['contest_status'] == 'running':
            data['progress_acc'] = int((timezone.now() - contest.start_time).total_seconds())
            data['progress_all'] = int((contest.end_time - contest.start_time).total_seconds())
            data['progress'] = int(data['progress_acc'] / data['progress_all'] * 100)
            data['time_delta'] = data['progress_all'] - data['progress_acc']
        elif data['contest_status'] == 'pending':
            data['progress'] = 0
            data['time_delta'] = int((contest.start_time - timezone.now()).total_seconds())
        data['contest_problem_list'] = contest.contestproblem_set.all()
        data['has_permission'] = self.test_func()

        if contest.freeze and data['contest_status'] == 'running' and timezone.now() > contest.freeze_time:
            data['is_frozen'] = True

        if is_admin_or_root(self.request.user):
            data['is_privileged'] = True

        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def test_func(self):
        if is_admin_or_root(self.request.user):
            return True
        return Contest.objects.get(pk=self.kwargs.get('cid')).visible

    def get_context_data(self, **kwargs):
        data = super(DashboardView, self).get_context_data(**kwargs)
        contest = data['contest']
        user = self.request.user
        problem_as_contest_problem = {}
        problem_status = {}

        if contest.public:
            data['registered'] = True
        elif user.is_authenticated and contest.contestparticipant_set.filter(user=user).exists():
            data['registered'] = True

        data['has_permission'] = super(DashboardView, self).test_func()
        if data['has_permission']:
            for contest_problem in data['contest_problem_list']:
                problem_as_contest_problem[contest_problem.problem.pk] = contest_problem.identifier
            if user.is_authenticated:

                submissions = contest.submission_set.filter(author=user).all()
                for submission in submissions:
                    try:
                        contest_problem = problem_as_contest_problem[submission.problem.pk]
                        if problem_status.get(contest_problem) != 'success':
                            if submission.status == SubmissionStatus.ACCEPTED:
                                problem_status[contest_problem] = 'success'
                            elif not SubmissionStatus.is_judged(submission.status):
                                problem_status[contest_problem] = 'warning'
                            elif SubmissionStatus.is_penalty(submission.status):
                                problem_status[contest_problem] = 'danger'
                    except KeyError:
                        pass

                for contest_problem in data['contest_problem_list']:
                    contest_problem.status = problem_status.get(contest_problem.identifier)

        return data


class ContestList(ListView):
    template_name = 'contest_list.jinja2'
    paginate_by = 50
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list(all=is_admin_or_root(self.request.user))


class ContestProblemDetail(BaseContestMixin, TemplateView):
    template_name = 'contest/problem.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestProblemDetail, self).get_context_data(**kwargs)
        data['contest_problem'] = get_object_or_404(ContestProblem,
                                                    identifier=self.kwargs.get('pid'),
                                                    contest=data['contest'])
        data['problem'] = data['contest_problem'].problem.get_markdown()
        return data


class ContestBoundUser(View):
    def post(self, request, cid):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
        else:
            invitation_code = request.POST.get('code', '')
            try:
                invitation = ContestInvitation.objects.get(code=invitation_code)
                add_participant_with_invitation(cid, invitation.pk, request.user)
                messages.success(request, 'You have successfully joined this contest.')
            except ContestInvitation.DoesNotExist:
                messages.error(request, 'There seems to be something wrong with your invitation code.')
        return HttpResponseRedirect(reverse('contest:dashboard', kwargs={'cid': cid}))
