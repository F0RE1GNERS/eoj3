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
                                               'problem__sample', 'problem__hint').all())
        self.is_frozen = self.contest.get_frozen()

        self.user = request.user
        self.privileged = is_admin_or_root(self.user)
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
        if self.contest.get_status() == 'pending':
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
        data['contest_status'] = self.contest.get_status()
        data['current_time'] = timezone.now()

        if data['contest_status'] == 'ended':
            data['progress'] = 100
        elif data['contest_status'] == 'running':
            data['progress_acc'] = int((timezone.now() - self.contest.start_time).total_seconds())
            data['progress_all'] = int((self.contest.end_time - self.contest.start_time).total_seconds())
            data['progress'] = int(data['progress_acc'] / data['progress_all'] * 100)
            data['time_delta'] = data['progress_all'] - data['progress_acc']
        elif data['contest_status'] == 'pending':
            data['progress'] = 0
            data['time_delta'] = int((self.contest.start_time - timezone.now()).total_seconds())
        data['contest_problem_list'] = self.contest_problem_list
        data['has_permission'] = self.test_func()
        data['is_frozen'] = self.is_frozen

        data['is_privileged'] = self.privileged

        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def test_func(self):
        if self.privileged:
            return True
        return self.contest.visible

    def get_context_data(self, **kwargs):
        data = super(DashboardView, self).get_context_data(**kwargs)
        problem_as_contest_problem = {}
        problem_status = {}

        if self.registered:
            data['registered'] = True

        data['has_permission'] = super(DashboardView, self).test_func()
        if data['has_permission']:
            for contest_problem in data['contest_problem_list']:
                problem_as_contest_problem[contest_problem.problem_id] = contest_problem.identifier
            if self.user.is_authenticated:
                submissions = self.contest.submission_set.filter(author=self.user).all()
                for submission in submissions:
                    try:
                        contest_problem = problem_as_contest_problem[submission.problem_id]
                        if problem_status.get(contest_problem) != 'success':
                            if submission.status == SubmissionStatus.ACCEPTED:
                                problem_status[contest_problem] = 'success'
                            elif not SubmissionStatus.is_judged(submission.status):
                                problem_status[contest_problem] = 'warning'
                            elif SubmissionStatus.is_penalty(submission.status):
                                problem_status[contest_problem] = 'danger'
                    except KeyError:
                        pass

                for contest_problem in self.contest_problem_list:
                    contest_problem.status = problem_status.get(contest_problem.identifier)

        return data


class ContestProblemDetail(BaseContestMixin, TemplateView):
    template_name = 'contest/problem.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ContestProblemDetail, self).get_context_data(**kwargs)
        data['contest_problem'] = get_object_or_404(ContestProblem,
                                                    identifier=self.kwargs.get('pid'),
                                                    contest=self.contest)
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



class ContestList(ListView):
    template_name = 'contest_list.jinja2'
    paginate_by = 50
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list(all=is_admin_or_root(self.request.user))
