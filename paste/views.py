from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import TemplateView

from account.models import User
from paste.forms import PasteForm, AnonymousPasteForm
from paste.models import Paste
from utils import random_string
from utils.language import transform_code_to_html


class PasteListAndCreateView(CreateView):
    template_name = 'paste/index.jinja2'

    def get_form_class(self):
        if self.request.user.is_authenticated:
            return PasteForm
        else:
            return AnonymousPasteForm

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            selected = Q(created_by=self.request.user)
            invited_pks = self.request.user.invited_pastes.values_list("pk", flat=True)
            selected |= Q(pk__in=invited_pks)
            data['paste_list'] = Paste.objects.filter(is_deleted=False).filter(selected).select_related("created_by"). \
                prefetch_related("invited_users").order_by("-create_time")
            data['paste_list'] = list(filter(lambda paste: not paste.expired, data['paste_list']))
        else:
            data['login_please'] = True
        return data

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.create_time = datetime.now()
            if self.request.user.is_authenticated:
                form.instance.created_by = self.request.user
            form.instance.fingerprint = random_string(8)
            self.object = form.save()
            if "invited_users" in form.cleaned_data:
                self.object.invited_users.add(*form.cleaned_data["invited_users"])
        return redirect(reverse('paste:detail', kwargs={'pk': self.object.fingerprint}))


class PasteDetailView(TemplateView):
    template_name = 'paste/detail.jinja2'

    def check_permission(self, paste, user):
        if paste.expired:
            return False
        if user.is_authenticated:
            if paste.created_by == user:
                return True
            if paste.public_access >= 10 and paste.invited_users.filter(pk=user.pk).exists():
                return True
        if paste.public_access >= 20:
            return True
        return False

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        try:
            paste = Paste.objects.get(fingerprint=self.kwargs["pk"])
        except:
            raise Http404
        if not self.check_permission(paste, self.request.user):
            raise PermissionDenied
        paste.code_as_html = transform_code_to_html(paste.code, paste.lang)
        data["paste"] = paste
        return data


class PasteDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):
        Paste.objects.filter(fingerprint=pk, created_by=self.request.user).update(is_deleted=True)
        return redirect(reverse('paste:index'))
