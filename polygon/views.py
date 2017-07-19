from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth import PermissionDenied
from django.views.generic import ListView, CreateView
from django.contrib import messages
from account.permissions import is_admin_or_root
from problem.models import Problem, ProblemManagement
from .session import init_session, pull_session
from .models import EditSession
import re


def home_view(request):
    return render(request, 'polygon/home.jinja2', context={'polygon_authorized': True})
    # TODO: polygon authorization


def register_view(request):
    template_name = 'polygon/register.jinja2'
    if request.method == 'GET':
        return render(request, template_name)
    else:
        if request.POST.get('terms') != 'on':
            return render(request, template_name, context={'register_error': 'You did\'nt accept terms of use.'})
        # TODO: or not authorized:
        request.user.polygon_enabled = True
        request.user.save(update_fields=['polygon_enabled'])
        return redirect(reverse('polygon:home'))


class SessionList(ListView):
    template_name = 'polygon/session_list.jinja2'
    paginate_by = 20
    context_object_name = 'problem_manage_list'

    def get_queryset(self):
        return self.request.user.problemmanagement_set.select_related("problem").\
            all().order_by("problem__update_time").reverse()

    def get_context_data(self, **kwargs):
        data = super(SessionList, self).get_context_data(**kwargs)
        data['problems'] = problems = []
        for problem_manage in data['problem_manage_list']:
            prob = problem_manage.problem
            prob.access_type = problem_manage.get_permission_display()
            prob.sessions = prob.editsession_set.select_related("problem", "user").all()
            problems.append(prob)
        data['problemset_count'] = Problem.objects.count()
        return data


def session_create(request):
    """
    It is actually "repository create"
    named "session create" for convenience
    """
    if request.method == 'POST':
        alias = request.POST['alias']
        assert re.match(r"^[a-z0-9_-]{4,64}$", alias)
        problem = Problem.objects.create(alias=alias)
        if is_admin_or_root(request.user):
            permission = 'a'
        else:
            permission = 'w'
        ProblemManagement.objects.create(problem=problem, user=request.user, permission=permission)
        init_session(problem, request.user)
        return redirect(request.POST['next'])


def session_pull(request):
    if request.method == 'POST':
        problem = get_object_or_404(Problem, id=request.POST['problem'])
        # verify permission
        try:
            if ProblemManagement.objects.get(problem=problem, user=request.user).permission == 'r':
                raise PermissionDenied
        except ProblemManagement.DoesNotExist:
            raise PermissionDenied
        try:
            session = EditSession.objects.get(problem=problem, user=request.user)
            pull_session(session)
        except EditSession.DoesNotExist:
            init_session(problem, request.user)
        messages.add_message(request, messages.SUCCESS, "Synchronization succeeded!")
        return redirect(request.POST['next'])
