from django.shortcuts import render
from .forms import ProblemEditForm


def index(request):
    return render(request, 'backstage/index.html', {'backstage_active': 'home'})


def problem(request):
    return render(request, 'backstage/problem.html', {'backstage_active': 'problem'})


def problem_add(request):
    problem_edit_form = ProblemEditForm()
    return render(request, 'backstage/problem_add.html', {'backstage_active': 'problem',
                                                          'form': problem_edit_form})
