from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.utils import timezone

from .models import Contest, ContestProblem
from problem.models import Problem


class BaseContextView(TemplateView):
    template_name = 'contest/index.html'

    def get_context_data(self, **kwargs):
        data = super(BaseContextView, self).get_context_data(**kwargs)
        contest = get_object_or_404(Contest, pk=self.kwargs['pk'])
        data['contest'] = contest
        remaining_time_seconds = (contest.end_time - timezone.now()).seconds
        data['progress'] = 100 - int(100 * remaining_time_seconds / (contest.end_time - contest.start_time).seconds)
        data['remaining_time'] = "%d:%.2d:%.2d" % (remaining_time_seconds // 3600,
                                                   remaining_time_seconds % 3600 // 60,
                                                   remaining_time_seconds % 60)
        data['contest_problem_list'] = get_list_or_404(ContestProblem, contest=data['contest'])
        return data


class ContestList(ListView):
    template_name = 'contest_list.html'
    paginate_by = 50
    context_object_name = 'contest_list'

    def get_queryset(self):
        return Contest.objects.get_status_list()


def dashboard(request, pk):
    return render(request, 'contest/index.html')


def standings(request, pk):
    return render(request, 'contest/standings.html')


class ContestProblemDetail(BaseContextView):
    template_name = 'contest/problem.html'

    def get_context_data(self, **kwargs):
        data = super(ContestProblemDetail, self).get_context_data(**kwargs)
        data['contest_problem'] = get_object_or_404(ContestProblem,
                                                    identifier=self.kwargs.get('pid'),
                                                    contest=data['contest'])
        data['problem'] = data['contest_problem'].problem.get_markdown()
        return data
