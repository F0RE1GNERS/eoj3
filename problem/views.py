from django.shortcuts import render
from django.views.generic.list import ListView
from .models import Problem


class ProblemList(ListView):
    template_name = 'problem_list.html'
    queryset = Problem.objects.all()
    paginate_by = 50
    context_object_name = 'problem_list'


def problem_view(request, problem_id):
    return render(request, 'problem.html')