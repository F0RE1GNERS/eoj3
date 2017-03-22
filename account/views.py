from django.shortcuts import render, redirect, HttpResponseRedirect, reverse
from django.views import View
from django.contrib import messages

from utils.auth_view import password_change, login
from .forms import RegisterForm, MyPasswordChangeForm


def profile_view(request):
    return render(request, 'account/profile.jinja2')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.create()
            login(request, user)
            return HttpResponseRedirect('/')
    else:
        form = RegisterForm()
    return render(request, 'register.jinja2', {'form': form})


def my_password_change(request):
    return password_change(request, template_name='account/security.jinja2',
                           post_change_redirect=reverse('account:profile'),
                           password_change_form=MyPasswordChangeForm,
                           message="Your password was changed successfully")


def my_login(request):
    return login(request, template_name='login.jinja2')
