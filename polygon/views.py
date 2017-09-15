from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from polygon.base_views import PolygonBaseMixin, response_ok
from polygon.models import Run
from polygon.rejudge import rejudge_submission, rejudge_all_submission_on_problem
from problem.models import Problem
from submission.models import Submission


def authorization(user):
    return False
    # TODO: open polygon
    # return get_accept_problem_count(user.id) >= 100


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


class RejudgeSubmission(PolygonBaseMixin, View):

    def dispatch(self, request, *args, **kwargs):
        self.submission = get_object_or_404(Submission, pk=kwargs.get('sid'))
        return super(RejudgeSubmission, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.submission.problem.problemmanagement_set.filter(
                user=self.request.user).exists() or self.submission.contest.managers.filter(
                user=self.request.user).exists():
            return super(RejudgeSubmission, self).test_func()
        return False

    def post(self, request, sid):
        rejudge_submission(self.submission)
        return HttpResponse()


class RejudgeProblem(PolygonBaseMixin, View):

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
        return super(RejudgeProblem, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.problem.problemmanagement_set.filter(user=self.request.user).exists():
            return super(RejudgeProblem, self).test_func()
        return False

    def post(self, request, pk):
        rejudge_all_submission_on_problem(self.problem)
        return redirect(reverse('polygon:problem_status', kwargs={'pk': self.problem.id}))


class RunsList(PolygonBaseMixin, ListView):
    template_name = 'polygon/runs.jinja2'
    paginate_by = 100
    context_object_name = 'runs_list'

    def get_queryset(self):
        return Run.objects.filter(user=self.request.user).order_by("-pk").all()


class RunMessageView(PolygonBaseMixin, View):

    def get(self, request, pk):
        try:
            run = Run.objects.get(pk=pk, user=request.user)
            return HttpResponse(run.message)
        except Run.DoesNotExist:
            return HttpResponse("")


class RunStatus(PolygonBaseMixin, View):

    def get(self, request, pk):
        return response_ok(run_status=Run.objects.get(pk=pk, user=request.user).status)