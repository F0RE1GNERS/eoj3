import random

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect, HttpResponseRedirect, reverse, get_object_or_404
from django.contrib.auth import PermissionDenied
from django.views import View
from django.views.generic.edit import UpdateView, FormView, UpdateView
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth import login
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from account.payment import create_payment, change_username
from account.permissions import is_admin_or_root
from utils import auth_view
from .forms import (RegisterForm, MyPasswordChangeForm, MySetPasswordForm, ProfileForm, PreferenceForm,
                    FeedbackForm, LoginForm)
from .models import User
from django.contrib.auth.decorators import login_required
# from utils.models import get_site_settings
from utils.identicon import Identicon
from migrate.views import verify_old_user, MigrationThread
try:
    from eoj3.local_settings import ADMIN_EMAIL_LIST
except ImportError:
    ADMIN_EMAIL_LIST = []


@method_decorator(login_required, 'dispatch')
class UpdateProfileView(UpdateView):
    template_name = 'account/profile.jinja2'
    form_class = ProfileForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        messages.success(self.request, 'Your changes have been saved.')
        return self.request.path


@method_decorator(login_required, 'dispatch')
class FeedbackView(FormView):
    form_class = FeedbackForm
    template_name = 'support/feedback.jinja2'

    def form_valid(self, form):
        data = form.cleaned_data
        message = "Username: {}, Email: {}\n".format(self.request.user.username, self.request.user.email) + data['content']
        if send_mail(subject=data['title'], message=message, from_email=None, recipient_list=ADMIN_EMAIL_LIST,
                     fail_silently=True):
            messages.success(self.request, "Your feedback has sent to administrator.")
        else:
            messages.error(self.request, "Your feedback failed to deliver. Please contact admin.")
        return HttpResponseRedirect(self.request.path)


@method_decorator(login_required, 'dispatch')
class UpdatePreferencesView(UpdateView):
    template_name = 'account/preference.jinja2'
    form_class = PreferenceForm
    context_object_name = "user"

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        messages.success(self.request, 'Your changes have been saved.')
        return self.request.path


class ChangeUsernameView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        username = request.POST["username"]
        if username != request.user.username:
            try:
                change_username(request.user, -100 * (request.user.username_change_attempt ** 2), username)
                request.user.username_change_attempt += 1
                request.user.save(update_fields=["username_change_attempt"])
            except PermissionError as e:
                messages.error(request, str(e))
        return HttpResponse()


class RegisterView(FormView):
    template_name = 'register.jinja2'
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.create()
        user.avatar.save('generated.png', Identicon(user.email).get_bytes())
        login(self.request, user)
        return HttpResponseRedirect(self.request.POST.get('next', self.request.GET.get('next', '/')))


def my_password_change(request):
    return auth_view.password_change(request, template_name='account/security.jinja2',
                                     post_change_redirect=reverse('account:profile'),
                                     password_change_form=MyPasswordChangeForm,
                                     message="Your password was changed successfully.")


def my_login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('home'))
    return auth_view.login(request, template_name='login.jinja2', authentication_form=LoginForm)


def my_password_reset(request):
    return auth_view.password_reset(request,
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


class BanAccount(UserPassesTestMixin, View):
    def test_func(self):
        return is_admin_or_root(self.request.user)

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return JsonResponse({})
