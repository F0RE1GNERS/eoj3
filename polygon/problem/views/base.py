from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import ContextMixin

from account.permissions import is_admin_or_root
from polygon.base_views import PolygonBaseMixin
from polygon.models import Revision
from problem.models import Problem
from utils.permission import is_problem_manager


class ProblemList(PolygonBaseMixin, ListView):
    template_name = 'polygon/problem/list.jinja2'
    context_object_name = 'problem_list'
    paginate_by = 250

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            return Problem.objects.all()
        else:
            return self.request.user.managing_problems.all()


class ProblemCreate(PolygonBaseMixin, View):

    def post(self, request, *args, **kwargs):
        problem = Problem.objects.create()
        problem.title = 'Problem #%d' % problem.id
        problem.alias = 'p%d' % problem.id
        problem.save(update_fields=['title', 'alias'])
        problem.managers.add(request.user)
        return HttpResponse()


class PolygonProblemMixin(ContextMixin, PolygonBaseMixin):
    raise_exception = True

    def init_revision(self, *args, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
        if is_problem_manager(self.request.user, self.problem):
            self.permission = 2

        self.init_revision(*args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """
        Permission 2: read & write
        Permission 1: read (will not accept post request)
        """
        if not super().test_func():
            return False
        if self.request.method == "POST" and self.permission < 2:
            return False
        elif self.permission < 1:
            return False
        return True

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['problem'] = self.problem
        return data


class ProblemRevisionMixin(PolygonProblemMixin):

    def init_revision(self, *args, **kwargs):
        self.revision = get_object_or_404(Revision, pk=kwargs.get('rpk'))
        if self.revision.user != self.request.user:
            self.permission = 1

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['revision'] = self.revision
        return data
