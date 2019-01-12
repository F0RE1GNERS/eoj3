from django import forms
from django.http import HttpResponse
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
from polygon.models import Run, Package, CodeforcesPackage
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
  template_name = 'register.jinja2'
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


class RunsList(PolygonBaseMixin, ListView):
  template_name = 'polygon/runs.jinja2'
  paginate_by = 100
  context_object_name = 'runs_list'

  def get_queryset(self):
    return Run.objects.filter(user=self.request.user).order_by("-pk").all()


class RunMessageView(PolygonBaseMixin, View):
  def get(self, request, pk):
    message = ''
    try:
      run = Run.objects.get(pk=pk, user=request.user)
      message = run.message
    except Run.DoesNotExist:
      pass
    return HttpResponse(message, content_type='text/plain')


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


class PackageLogsDownload(PolygonBaseMixin, DetailView):
  def get_queryset(self):
    return CodeforcesPackage.objects.filter(created_by=self.request.user, status__gte=0)

  def get(self, request, *args, **kwargs):
    self.object = self.get_object()
    response = HttpResponse(codeforces.pack_log_files(self.object), content_type="application/force-download")
    response["Content-Disposition"] = 'attachment; filename="{}$log.zip"'.format(self.object.id)
    return response


class PackageDownload(PolygonBaseMixin, DetailView):
  def get_queryset(self):
    return CodeforcesPackage.objects.filter(created_by=self.request.user, status=0)

  def get(self, request, *args, **kwargs):
    self.object = self.get_object()
    response = HttpResponse(codeforces.pack_log_files(self.object), content_type="application/force-download")
    response["Content-Disposition"] = 'attachment; filename="{}$log.zip"'.format(self.object.id)
    return response