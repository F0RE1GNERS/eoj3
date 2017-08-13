from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.list import ListView

from account.permissions import is_admin_or_root, is_volunteer
from problem.statistics import get_many_problem_accept_count
from submission.statistics import get_accept_problem_list, get_attempted_problem_list
from submission.models import SubmissionStatus
from .models import Contest, ContestProblem, ContestInvitation
from .tasks import add_participant_with_invitation


def time_formatter(seconds):
    return "%d:%.2d:%.2d" % (seconds // 3600,
                             seconds % 3600 // 60,
                             seconds % 60)


def get_contest_problem(contest_problem_list, problem_id):
    get_result = list(filter(lambda p: p.problem_id == problem_id, contest_problem_list))
    if len(get_result) > 0:
        return get_result[0]
    else:
        return 'N/A'


class BaseContestMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):
    raise_exception = True  # TODO show permission denied message

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('cid'))
        self.contest_problem_list = list(self.contest.contestproblem_set.select_related('problem').
                                         defer('problem__description', 'problem__input', 'problem__output',
                                               'problem__hint').all())

        self.user = request.user
        self.privileged = is_admin_or_root(self.user) or self.contest.manager.filter(user=self.user).exists()
        self.volunteer = is_volunteer(self.user)
        if self.user.is_authenticated and self.contest.contestparticipant_set.filter(user=self.user).exists():
            self.registered = True
        elif self.contest.public:
            self.registered = True
        else:
            self.registered = False
        return super(BaseContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.privileged:
            return True
        if not self.contest.visible:
            self.permission_denied_message = 'Contest is not visible.'
            return False
        if self.contest.status == 'pending':
            self.permission_denied_message = "Contest hasn't started."
            return False
        if self.registered:
            return True
        else:
            self.permission_denied_message = "Did you forget to register for the contest?"
            return False

    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        data['contest_status'] = self.contest.status
        data['current_time'] = timezone.now()
        if not self.contest.always_running:
            data['time_remaining'] = 0
            if data['contest_status'] < 0:
                data['time_remaining'] = (self.contest.start_time - data['current_time']).total_seconds()
            elif data['contest_status'] == 0:
                data['time_remaining'] = (self.contest.end_time - data['current_time']).total_seconds()
            data['time_all'] = 0
            if data['contest_status'] == 0:
                data['time_all'] = (self.contest.end_time - self.contest.start_time).total_seconds()
        data['contest_problem_list'] = self.contest_problem_list
        data['has_permission'] = self.test_func()
        data['is_privileged'] = self.privileged
        data['is_volunteer'] = self.volunteer

        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def test_func(self):
        if self.privileged:
            return True
        return self.contest.visible

    def get_context_data(self, **kwargs):
        data = super(DashboardView, self).get_context_data(**kwargs)

        if self.registered:
            data['registered'] = True

        data['has_permission'] = super(DashboardView, self).test_func()
        if data['has_permission']:
            if self.user.is_authenticated:
                attempt_list = set(get_attempted_problem_list(self.request.user.id, self.contest.id))
                accept_list = set(get_accept_problem_list(self.request.user.id, self.contest.id))
                for problem in data['contest_problem_list']:
                    if problem.problem_id in accept_list:
                        problem.personal_label = 1
                    elif problem.problem_id in attempt_list:
                        problem.personal_label = -1
                    else:
                        problem.personal_label = 0
        accept_count = get_many_problem_accept_count(list(map(lambda x: x.problem_id, data['contest_problem_list'])),
                                                     self.contest.id)
        for problem in data['contest_problem_list']:
            problem.accept_count = accept_count[problem.problem_id]

        return data


class ContestProblemDetail(BaseContestMixin, TemplateView):
    template_name = 'contest/problem.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestProblemDetail, self).get_context_data(**kwargs)
        data['contest_problem'] = get_object_or_404(ContestProblem,
                                                    identifier=self.kwargs.get('pid'),
                                                    contest=self.contest)
        data['problem'] = data['contest_problem'].problem
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


class ContestList(ListView):
    template_name = 'contest_list.jinja2'
    paginate_by = 30
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list(all=is_admin_or_root(self.request.user), always_running=False)


class ContestAlwaysRunningList(ListView):
    template_name = 'contest_always_running.jinja2'
    paginate_by = 30
    context_object_name = 'contest_list'

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        return Contest.objects.get_status_list(all=is_admin_or_root(self.request.user), filter_user=user,
                                               sorting_by_id=True, always_running=True)