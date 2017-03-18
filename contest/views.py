from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse
from django.db import transaction
from django.views.generic.list import ListView
from django.views.generic.base import TemplateResponseMixin, TemplateView
from django.views.generic.edit import FormView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.views.generic.base import TemplateResponseMixin, ContextMixin

from .models import Contest, ContestProblem
from submission.models import Submission
from problem.models import Problem
from submission.forms import ContestSubmitForm
from dispatcher.tasks import DispatcherThread


class BaseContestMixin(TemplateResponseMixin, ContextMixin):
    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])
        data['contest'] = contest
        remaining_time_seconds = (contest.end_time - timezone.now()).seconds
        data['progress'] = 100 - int(100 * remaining_time_seconds / (contest.end_time - contest.start_time).seconds)
        data['remaining_time'] = "%d:%.2d:%.2d" % (remaining_time_seconds // 3600,
                                                   remaining_time_seconds % 3600 // 60,
                                                   remaining_time_seconds % 60)
        data['contest_problem_list'] = get_list_or_404(ContestProblem, contest=data['contest'])
        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.html'


class ContestList(ListView):
    template_name = 'contest_list.html'
    paginate_by = 50
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list()


class ContestStandings(BaseContestMixin, TemplateView):
    template_name = 'contest/standings.html'


class ContestSubmit(BaseContestMixin, FormView):
    template_name = 'contest/submit.html'
    form_class = ContestSubmitForm

    def get_initial(self):
        return {'problem_identifier': self.request.GET.get('pid', '')}

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
        return HttpResponseRedirect(reverse('contest:standings', kwargs={'cid': contest.pk}))


class ContestMySubmission(BaseContestMixin, ListView):
    template_name = 'contest/submission.html'
    paginate_by = 20
    context_object_name = 'submission_list'

    def get_queryset(self):
        return Submission.objects.filter(contest=Contest.objects.get(pk=self.kwargs.get('cid')),
                                         author=self.request.user).all()


class ContestProblemDetail(BaseContestMixin, TemplateView):
    template_name = 'contest/problem.html'

    def get_context_data(self, **kwargs):
        data = super(ContestProblemDetail, self).get_context_data(**kwargs)
        data['contest_problem'] = get_object_or_404(ContestProblem,
                                                    identifier=self.kwargs.get('pid'),
                                                    contest=data['contest'])
        data['problem'] = data['contest_problem'].problem.get_markdown()
        return data
