from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import ProblemEditForm


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
