import random
from django.shortcuts import render, redirect, HttpResponseRedirect, reverse, get_object_or_404
from django.contrib.auth import PermissionDenied
from django.views import View
from django.views.generic.edit import UpdateView
from django.contrib import messages
from django.contrib.auth import login
from utils import auth_view
from .forms import RegisterForm, MyPasswordChangeForm, MySetPasswordForm, ProfileForm, PreferenceForm, MigrateForm
from .models import User, ALIEN_CHOICE
from django.contrib.auth.decorators import login_required
from utils.models import get_site_settings
from migrate.views import verify_old_user, MigrationThread


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your changes have been saved.')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'account/profile.jinja2', {'form': form})


@login_required
def update_preferences(request):
    if request.method == 'POST':
        form = PreferenceForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your changes have been saved.')
    else:
        form = PreferenceForm(instance=request.user)

    return render(request, 'account/preference.jinja2', {'form': form})


@login_required
def migrate_from_old(request):
    if not get_site_settings().migrate_open:
        raise PermissionDenied('Migration has not opened yet.')
    if request.method == 'POST':
        form = MigrateForm(request.POST)
        form.full_clean()
        result = form.clean()
        username = result.get('username')
        password = result.get('password')
        if verify_old_user(username, password):
            MigrationThread(username, request.user).start()
            messages.success(request, 'It could take a few minutes for the changes to take effect.')
        else:
            messages.error(request, 'Username or password wrong.')
    else:
        form = MigrateForm()

    return render(request, 'account/migrate.jinja2', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.create()
            user.alien = random.choice(list(dict(ALIEN_CHOICE).keys()))
            user.save(update_fields=["alien"])
            login(request, user)
            return HttpResponseRedirect(request.POST.get('next', request.GET.get('next', '/')))
    else:
        form = RegisterForm()
    return render(request, 'register.jinja2', {'form': form})


def my_password_change(request):
    return auth_view.password_change(request, template_name='account/security.jinja2',
                                     post_change_redirect=reverse('account:profile'),
                                     password_change_form=MyPasswordChangeForm,
                                     message="Your password was changed successfully.")


def my_login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('home'))
    return auth_view.login(request, template_name='login.jinja2')


def my_password_reset(request):
    return auth_view.password_reset(request,
                                    from_email="noreply@zerol.me",
                                    template_name='account/password_reset.jinja2',
                                    post_reset_redirect='account:password_reset_done',
                                    email_template_name='account/password_reset_email.jinja2')


def my_password_reset_done(request):
    return auth_view.password_reset_done(request, template_name='account/password_reset_done.jinja2')


def my_password_reset_confirm(request, **kwargs):
    return auth_view.password_reset_confirm(request,
                                            template_name='account/password_reset_confirm.jinja2',
                                            post_reset_redirect=reverse('login'),
                                            set_password_form=MySetPasswordForm,
                                            **kwargs)

