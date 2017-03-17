from django.shortcuts import render
from django.views.generic.list import ListView
from .models import Contest
from problem.models import Problem


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


def problem(request, pk, pid):
    problem = Problem.objects.get(**kwargs)
    form = self.form_class()
    body = markdown3.convert(problem.description)
    data = dict(problem=problem, form=form, body=body)
    return render(request, self.template_name, data)
