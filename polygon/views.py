from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from account.permissions import is_coach
from polygon.base_views import PolygonBaseMixin
from polygon.models import Run
from polygon.rejudge import rejudge_submission, rejudge_all_submission_on_problem
from problem.models import Problem
from submission.models import Submission
from utils.permission import is_problem_manager, is_contest_manager


def authorization(user):
    return is_coach(user)


def home_view(request):
    return render(request, 'polygon/home.jinja2', context={'polygon_authorized': authorization(request.user)})


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
                is_contest_manager(self.request.user, self.submission.contest):
            return super(RejudgeSubmission, self).test_func()
        return False

    def post(self, request, sid):
        rejudge_submission(self.submission)
        return Response()


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
