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

from .models import Contest, ContestProblem, ContestParticipant
from submission.models import Submission, SubmissionStatus
from account.models import Privilege
from problem.models import Problem
from submission.forms import ContestSubmitForm
from dispatcher.tasks import DispatcherThread


def time_formatter(seconds):
    return "%d:%.2d:%.2d" % (seconds // 3600,
                             seconds % 3600 // 60,
                             seconds % 60)


def get_contest_problem(contest, problem):
    return contest.contestproblem_set.get(problem=problem)


class BaseContestMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (ContestParticipant.objects.filter(
            contest=Contest.objects.get(pk=self.kwargs.get('cid')),
            user=user
        ).exists() or user.privilege in (Privilege.ROOT, Privilege.ADMIN))

    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])
        data['contest'] = contest
        data['contest_status'] = contest.get_status()
        if data['contest_status'] == 'Ended':
            data['progress'] = 100
        elif data['contest_status'] == 'Running':
            remaining_time_seconds = int((contest.end_time - timezone.now()).total_seconds())
            data['progress'] = 100 - int(100 * remaining_time_seconds / (contest.end_time - contest.start_time).total_seconds())
            data['remaining_time'] = 'Remaining ' + time_formatter(remaining_time_seconds)
        elif data['contest_status'] == 'Pending':
            data['progress'] = 0
            before_start_time_seconds = int((contest.start_time - timezone.now()).total_seconds())
            data['remaining_time'] = 'Before start ' + time_formatter(before_start_time_seconds)
        data['contest_problem_list'] = contest.contestproblem_set.all()
        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def get_context_data(self, **kwargs):
        data = super(DashboardView, self).get_context_data(**kwargs)
        contest = data['contest']
        user = self.request.user
        problem_as_contest_problem = {}
        problem_status = {}
        for contest_problem in data['contest_problem_list']:
            problem_as_contest_problem[contest_problem.problem.pk] = contest_problem.identifier
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
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])
        with transaction.atomic():
            submission = form.save(commit=False)
            problem_identifier = form.cleaned_data['problem_identifier']
            contest_problem = contest.contestproblem_set.select_for_update().get(identifier=problem_identifier)
            submission.problem = Problem.objects.select_for_update().get(pk=contest_problem.problem.pk)
            submission.contest = contest
            submission.author = self.request.user
            submission.code_length = len(submission.code)
            submission.save()

            contest_problem.add_submit()
            submission.problem.add_submit()
            contest_problem.save()
            submission.problem.save()

            DispatcherThread(submission.problem.pk, submission.pk).start()
        return HttpResponseRedirect(reverse('contest:submission', kwargs={'cid': contest.pk}))


class ContestMySubmission(BaseContestMixin, ListView):
    template_name = 'contest/submission.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        return Submission.objects.filter(contest=Contest.objects.get(pk=self.kwargs.get('cid')),
                                         author=self.request.user).all()

    def get_context_data(self, **kwargs):
        data = super(ContestMySubmission, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - data['contest'].start_time).seconds)
            submission.contest_problem = str(get_contest_problem(data['contest'], submission.problem))
        return data


class ContestStatus(BaseContestMixin, ListView):
    template_name = 'contest/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        return Submission.objects.filter(contest=Contest.objects.get(pk=self.kwargs.get('cid'))).all()

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

