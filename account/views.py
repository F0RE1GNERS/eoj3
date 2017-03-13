from django.shortcuts import render, redirect
from .forms import RegisterForm
from django.contrib.auth import login


def login_view(request):
    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        form.full_clean()
        if form.is_valid():
            user = form.save()
            login(request, user)
            redirect('/')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})
