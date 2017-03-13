from django.shortcuts import render


def index(request):
    return render(request, 'backstage/index.html', {'backstage_active': 'home'})

def add_problem(request):
    return render(request, 'backstage/add_problem.html', {'backstage_active': 'add_problem'})
