from django.shortcuts import render


def problem_list_view(request):
    return render(request, 'problem.html')


def problem_view(request):
    return render(request, 'problem.html')