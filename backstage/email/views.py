import traceback
from datetime import datetime, timedelta

from django import forms
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.shortcuts import HttpResponse, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView
from django.views.generic.list import ListView
from django_q.tasks import async_task

from account.models import User
from backstage.models import Email, EmailRecipient
from ..base_views import BaseBackstageMixin, BaseCreateView


class EmailForm(forms.ModelForm):
  class Meta:
    model = Email
    fields = ['title', 'content']


class EmailCreateView(BaseCreateView):
  template_name = 'backstage/email/create.jinja2'
  form_class = EmailForm

  def get_object(self, queryset=None):
    try:
      obj = Email.objects.get(pk=self.kwargs["eid"])
    except Email.DoesNotExist:
      raise Http404
    return obj

  def get_redirect_url(self, instance):
    return reverse('backstage:email')


class EmailList(BaseBackstageMixin, ListView):
  template_name = 'backstage/email/list.jinja2'
  queryset = Email.objects.all().order_by("-pk")
  paginate_by = 100
  context_object_name = 'email_list'


class EmailUpdateView(BaseBackstageMixin, UpdateView):
  template_name = 'backstage/email/detail.jinja2'
  form_class = EmailForm
  context_object_name = 'email'

  def get_object(self, queryset=None):
    try:
      obj = Email.objects.get(pk=self.kwargs["eid"])
    except Email.DoesNotExist:
      raise Http404
    return obj

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data['recipients'] = EmailRecipient.objects.filter(email=self.object).select_related("user").all()
    return data

  def get_success_url(self):
    return reverse('backstage:email_update', kwargs=self.kwargs)


class EmailAddRecipient(BaseBackstageMixin, View):
  def post(self, request, eid):
    email = get_object_or_404(Email, pk=eid)
    text = self.request.POST.get('text', '')
    if text == "#all#":
      users = User.objects.filter(is_active=True, email_subscription=True,
                                  last_login__gte=datetime.now() - timedelta(days=180)). \
        exclude(username__contains='#').order_by("-last_login")
    else:
      users = User.objects.filter(username=text)
    with transaction.atomic():
      for user in users:
        EmailRecipient.objects.get_or_create(email=email, user=user)
    return redirect(reverse('backstage:email_update', kwargs={'eid': eid}))


class EmailDeleteRecipient(BaseBackstageMixin, View):
  def post(self, request, pk):
    t = EmailRecipient.objects.get(pk=pk)
    email_id = t.email_id
    t.delete()
    return redirect(reverse('backstage:email_update', kwargs={'eid': email_id}))


class EmailRecipientErrorReport(BaseBackstageMixin, View):
  def get(self, request, pk):
    t = EmailRecipient.objects.get(pk=pk).error_message
    return HttpResponse(t, content_type='text/plain')


class EmailPreview(BaseBackstageMixin, View):
  def get(self, request, eid):
    email = get_object_or_404(Email, pk=eid)
    return HttpResponse(email.content)


class EmailSend(BaseBackstageMixin, View):

  @staticmethod
  def send(email, recipients):
    for recipient in recipients:
      head = email.title
      msg = email.content.replace('$$user$$', recipient.user.username)
      try:
        send_mail(subject=head, message='', from_email=None, recipient_list=[recipient.user.email],
                  html_message=msg)
        recipient.error_message = ''
        recipient.status = 0
        recipient.save()
      except:
        recipient.error_message = traceback.format_exc()
        recipient.status = 1
        recipient.save()

  def post(self, request, eid):
    email = get_object_or_404(Email, pk=eid)
    if 't' in self.request.GET:
      recipients = EmailRecipient.objects.filter(email=email, pk=self.request.GET['t']).select_related("user")
    else:
      recipients = EmailRecipient.objects.filter(email=email).exclude(status=0).select_related("user")
    async_task(EmailSend.send, email, list(recipients))
    return redirect(reverse('backstage:email_update', kwargs={'eid': eid}))
