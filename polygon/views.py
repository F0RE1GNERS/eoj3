from abc import abstractmethod

from django import forms
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, FormView, DetailView
from django_q.tasks import async_task
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from account.permissions import is_coach
from polygon.base_views import PolygonBaseMixin
from polygon.models import Package, CodeforcesPackage
from polygon.package import codeforces
from polygon.rejudge import rejudge_submission, rejudge_all_submission_on_problem
from problem.models import Problem
from submission.models import Submission
from utils.permission import is_problem_manager, is_contest_manager


def authorization(user):
  return is_coach(user)


def home_view(request):
  return render(request, 'polygon/polygon_home.jinja2', context={'polygon_authorized': authorization(request.user)})


def register_view(request):
  template_name = 'polygon/register.jinja2'
  if request.method == 'GET':
    return render(request, template_name)
  else:
    if request.POST.get('terms') != 'on':
      return render(request, template_name, context={'register_error': 'You did\'nt accept terms of use.'})
    if not authorization(request.user):
      return render(request, template_name, context={'register_error': 'You are not authorized.'})
    request.user.polygon_enabled = True
    request.user.save(update_fields=['polygon_enabled'])
    return redirect(reverse('polygon:home'))


class RejudgeSubmission(PolygonBaseMixin, APIView):

  def dispatch(self, request, *args, **kwargs):
    self.submission = get_object_or_404(Submission, pk=kwargs.get('sid'))
    return super(RejudgeSubmission, self).dispatch(request, *args, **kwargs)

  def test_func(self):
    if is_problem_manager(self.request.user, self.submission.problem) or \
        (self.submission.contest and is_contest_manager(self.request.user, self.submission.contest)):
      return super(RejudgeSubmission, self).test_func()
    return False

  def post(self, request, sid):
    async_task(rejudge_submission, self.submission, run_until_complete='all' in request.GET)
    if self.submission.contest_id:
      nxt = reverse('contest:submission', kwargs={'cid': self.submission.contest_id, 'sid': self.submission.id})
    else:
      nxt = reverse('problem:submission', kwargs={'pk': self.submission.problem_id, 'sid': self.submission.id})
    return redirect(nxt)


class PackageView(PolygonBaseMixin, ListView):
  def get_queryset(self):
    return CodeforcesPackage.objects.filter(created_by=self.request.user).order_by("-create_time")

  template_name = "polygon/package.jinja2"
  context_object_name = "package_list"


class PackageCreate(PolygonBaseMixin, FormView):
  class PackageCreateForm(forms.Form):
    answer = forms.CharField()

  form_class = PackageCreateForm

  def get_success_url(self):
    return reverse("polygon:packages")

  def form_valid(self, form):
    codeforces.create_task(form.cleaned_data["answer"], self.request.user)
    return super().form_valid(form)


class DownloadDetailView(DetailView):
  @abstractmethod
  def get_content(self, object):
    pass

  @abstractmethod
  def get_filename(self, object):
    pass

  def get(self, request, *args, **kwargs):
    self.object = self.get_object()
    response = HttpResponse(self.get_content(self.object), content_type="application/force-download")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(self.get_filename(self.object))
    return response


class PackageLogsDownload(PolygonBaseMixin, DownloadDetailView):
  def get_queryset(self):
    return CodeforcesPackage.objects.filter(created_by=self.request.user, status__gte=0)

  def get_content(self, object):
    return codeforces.pack_log_files(object)

  def get_filename(self, object):
    return "{}$log.zip".format(object.id)


class PackageDownload(PolygonBaseMixin, DownloadDetailView):
  def get_queryset(self):
    return CodeforcesPackage.objects.filter(created_by=self.request.user, status=0)

  def get_object(self, queryset=None):
    object = super().get_object(queryset)
    if object.short_name is None or object.revision is None:
      raise Http404
    return object

  def get_content(self, object):
    return codeforces.pack_package(object)

  def get_filename(self, object):
    return "{}${}.zip".format(object.short_name, object.revision)