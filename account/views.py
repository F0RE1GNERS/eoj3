from django.shortcuts import render, redirect, HttpResponseRedirect
from .forms import RegisterForm, LoginForm
from django.contrib.auth import login, authenticate, logout

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():  # TODO authenticate twice
            user = authenticate(username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password'))
            login(request, user)
            return HttpResponseRedirect(request.POST.get('next', '/'))
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.create()
            login(request, user)
            redirect('/')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/')
