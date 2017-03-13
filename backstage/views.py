from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import ProblemEditForm
from problem.models import Problem


def index(request):
    return render(request, 'backstage/index.html', {'backstage_active': 'home'})


def problem(request):
    return render(request, 'backstage/problem.html', {'backstage_active': 'problem'})


@login_required()
def problem_add(request):
    if request.method == 'POST':
        form = ProblemEditForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.created_by = request.user
            instance.save()
            messages.add_message(request, messages.SUCCESS, "Problem was successfully added.")
    else:
        form = ProblemEditForm()
    return render(request, 'backstage/problem_add.html', {'backstage_active': 'problem',
                                                          'form': form})

@login_required()
def problem_edit(request, problem_pk):
    instance = Problem.objects.get(pk=problem_pk)
    if request.method == 'POST':
        form = ProblemEditForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, "Problem was successfully edited.")
    else:
            form = ProblemEditForm(instance=instance)
    return render(request, 'backstage/problem_edit.html', {'backstage_active': 'problem',
                                                          'form': form})
