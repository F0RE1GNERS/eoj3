from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse
from django.db import transaction
from django.views.generic.list import ListView
from django.views.generic.base import TemplateResponseMixin, TemplateView
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Contest, ContestProblem, ContestParticipant, ContestInvitation
from .tasks import add_participant_with_invitation, update_contest
from submission.models import Submission, SubmissionStatus
from submission.forms import ContestSubmitForm
from dispatcher.tasks import submit_code_for_contest
from account.permissions import is_admin_or_root


def time_formatter(seconds):
    return "%d:%.2d:%.2d" % (seconds // 3600,
                             seconds % 3600 // 60,
                             seconds % 60)


def get_contest_problem(contest, problem):
    return contest.contestproblem_set.get(problem=problem)


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

        if is_admin_or_root(self.request.user):
            data['is_privileged'] = True

        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def test_func(self):
        return True

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
                    contest_problem = problem_as_contest_problem[submission.problem.pk]
                    if problem_status.get(contest_problem) != 'success':
                        if submission.status == SubmissionStatus.ACCEPTED:
                            problem_status[contest_problem] = 'success'
                        elif not SubmissionStatus.is_judged(submission.status):
                            problem_status[contest_problem] = 'warning'
                        elif SubmissionStatus.is_penalty(submission.status):
                            problem_status[contest_problem] = 'danger'

                for contest_problem in data['contest_problem_list']:
                    contest_problem.status = problem_status.get(contest_problem.identifier)

        return data


class ContestList(ListView):
    template_name = 'contest_list.jinja2'
    paginate_by = 50
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list()


class ContestStandings(BaseContestMixin, TemplateView):
    template_name = 'contest/standings.jinja2'

    def get_queryset(self):
        return Contest.objects.get(pk=self.kwargs.get('cid')).contestparticipant_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestStandings, self).get_context_data(**kwargs)
        contest = data['contest']
        data['rank_list'] = list(enumerate(contest.contestparticipant_set.all(), start=1))
        data['my_rank'] = 'N/A'
        data['update_time'] = contest.standings_update_time
        for (rank, detail) in data['rank_list']:
            if detail.user == self.request.user:
                data['my_rank'] = rank
        return data


class ContestSubmit(BaseContestMixin, FormView):
    template_name = 'contest/submit.jinja2'
    form_class = ContestSubmitForm

    def get_initial(self):
        return {'problem_identifier': self.request.GET.get('pid', '')}

    def get_form_kwargs(self):
        kwargs = super(ContestSubmit, self).get_form_kwargs()
        kwargs['contest_problem_list'] = get_object_or_404(Contest, pk=self.kwargs['cid']).contestproblem_set.all()
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Please login first.')
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])
        if timezone.now() < contest.start_time or timezone.now() > contest.end_time:
            messages.error(self.request, 'You are currently not in the period of the contest.')
            return HttpResponseRedirect(self.request.path)
        submission = form.save(commit=False)
        problem_identifier = form.cleaned_data['problem_identifier']
        submit_code_for_contest(submission, self.request.user, problem_identifier, contest)
        return HttpResponseRedirect(reverse('contest:submission', kwargs={'cid': self.kwargs['cid']}))


class ContestMySubmission(BaseContestMixin, ListView):
    template_name = 'contest/submission.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Please login first.')
        return Submission.objects.filter(contest=Contest.objects.get(pk=self.kwargs.get('cid')),
                                         author=self.request.user).all()

    def get_context_data(self, **kwargs):
        data = super(ContestMySubmission, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - data['contest'].start_time).seconds)
            submission.contest_problem = get_contest_problem(data['contest'], submission.problem)
        return data


class ContestStatus(BaseContestMixin, ListView):
    template_name = 'contest/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        contest = Contest.objects.get(pk=self.kwargs.get('cid'))
        if not is_admin_or_root(self.request.user) and contest.freeze and contest.get_status() == 'running':
            return Submission.objects.filter(contest=contest, create_time__lt=contest.freeze_time).all()
        else:
            return Submission.objects.filter(contest=contest).all()

    def get_context_data(self, **kwargs):
        data = super(ContestStatus, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - data['contest'].start_time).seconds)
        return data


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


class ContestUpdateStandings(View):
    def get(self, request, cid):
        if not is_admin_or_root(request.user):
            raise PermissionDenied('You cannot update the standings')
        update_contest(Contest.objects.get(pk=cid))
        return HttpResponseRedirect(reverse('contest:standings', kwargs={'cid': cid}))
