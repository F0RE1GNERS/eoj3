import traceback
from itertools import chain

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import ContextMixin, TemplateView

from account.models import User
from account.permissions import is_admin_or_root
from polygon.base_views import PolygonBaseMixin
from polygon.models import Revision
from polygon.rejudge import rejudge_all_submission_on_problem
from problem.models import Problem
from problem.views import StatusList
from submission.models import Submission
from utils.permission import is_problem_manager


class ProblemList(PolygonBaseMixin, ListView):
    template_name = 'polygon/problem2/list.jinja2'
    context_object_name = 'problem_list'
    paginate_by = 250

    def get_queryset(self):
        if 'q' in self.request.GET:
            self.search_text = q = self.request.GET['q']
            query = Q(title__icontains=q) | Q(alias__icontains=q) | Q(source__icontains=q)
            if q.isdigit():
                query |= Q(pk__exact=q)
        else:
            self.search_text = ''
            query = None

        if is_admin_or_root(self.request.user):
            qs = Problem.objects.all()
        else:
            qs = self.request.user.managing_problems.all()
        if query:
            qs = qs.filter(query)
        qs = qs.prefetch_related("revisions").annotate(Count('revisions'))
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        for problem in data['problem_list']:
            problem.latest_revision, problem.my_latest_revision = None, None
            for revision in sorted(problem.revisions.all(), key=lambda x: x.create_time, reverse=True):
                problem.latest_revision = revision
                break
        data['search_text'] = self.search_text
        return data


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
    post_allowed_for_low_permission = False

    def init_revision(self, *args, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
        self.latest_revisions = self.problem.revisions.all().order_by("-revision")[:5]
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
        if self.request.method == "POST" and self.permission < 2 and not self.post_allowed_for_low_permission:
            return False
        elif self.permission < 1:
            return False
        return True

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['problem'] = self.problem
        data['latest_revisions'] = self.latest_revisions
        return data


class ProblemRevisionMixin(PolygonProblemMixin):
    model_class = None

    def verify_belong_to_revision(self, id):
        def expand_queryset(qs):
            return set(chain(*qs.values_list("id", "parent_id"))) - {0}

        if self.model_class is None:
            raise NotImplementedError("\"model_class\" should not be None when checking revision")
        if isinstance(id, str) and id.isdigit():
            id = int(id)
        qs = self.model_class.objects.filter(revision=self.revision.id)
        ret = set()
        while True:
            ret_nxt = expand_queryset(qs)
            if ret_nxt == ret: break
            ret = ret_nxt
            if id in ret: return True
            qs = self.model_class.objects.filter(id__in=ret)
        return False

    def init_revision(self, *args, **kwargs):
        self.revision = self.problem.revisions.select_related("active_statement", "active_checker", "active_validator",
                                                              "active_interactor", "user").filter(pk=kwargs['rpk'])
        if len(self.revision) == 0:
            raise Http404("Revision matches not found.")
        else: self.revision = self.revision[0]
        if self.revision.user != self.request.user or self.revision.status != 0:
            self.permission = 1

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['revision'] = self.revision
        return data


class ProblemStatus(PolygonProblemMixin, StatusList):
    template_name = 'polygon/problem2/status.jinja2'
    privileged = True

    def get_selected_from(self):
        return Submission.objects.filter(problem_id=self.problem.id)


class ProblemRejudge(PolygonProblemMixin, View):
    def post(self, request, *args, **kwargs):
        rejudge_all_submission_on_problem(self.problem)
        return redirect(reverse('polygon:problem_status', kwargs={'pk': self.problem.id}))


class ProblemBasicInfoManage(PolygonProblemMixin, TemplateView):
    """
    This includes admin and alias
    """
    template_name = 'polygon/problem2/basic_info.jinja2'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['admin_list'] = self.problem.managers.all()
        return data

    @transaction.atomic()
    def post(self, request, pk):
        self.problem.alias = request.POST['alias']
        self.problem.source = request.POST['source']
        my_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        self.problem.managers.clear()
        for key in my_set:
            self.problem.managers.add(User.objects.get(pk=key))
        self.problem.save()
        return redirect(self.request.path)
