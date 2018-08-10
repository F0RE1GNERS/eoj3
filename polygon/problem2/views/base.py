import traceback
from itertools import chain

from django.contrib import messages
from django.core.exceptions import PermissionDenied
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
from contest.models import Contest
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
        if 'exact' in self.request.GET:
            self.search_text = q = self.request.GET['exact']
            query = Q(pk__exact=q)
        elif 'q' in self.request.GET:
            self.search_text = q = self.request.GET['q']
            query = Q(title__icontains=q) | Q(alias__icontains=q) | Q(source__icontains=q)
            if q.isdigit():
                query |= Q(pk__exact=q)
                self.id_searching_recommendation = q
        else:
            self.search_text = ''
            query = None

        if is_admin_or_root(self.request.user):
            qs = Problem.objects.all()
        else:
            qs = self.request.user.managing_problems.all()
        if query:
            qs = qs.filter(query)
        qs = qs.order_by("-update_time").prefetch_related("revisions").annotate(Count('revisions'))
        return qs

    @staticmethod
    def get_problem_latest_revision(problem):
        problem.latest_revision, problem.my_latest_revision = None, None
        for revision in sorted(problem.revisions.all(), key=lambda x: x.create_time, reverse=True):
            return revision

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        for problem in data['problem_list']:
            problem.latest_revision = self.get_problem_latest_revision(problem)
        data['search_text'] = self.search_text
        if hasattr(self, "id_searching_recommendation"):
            pid = self.id_searching_recommendation
            if Problem.objects.filter(id=pid).exists() and \
                    is_admin_or_root(self.request.user) or self.request.user.managing_problems.filter(id=pid).exists():
                data["suggest_problem"] = Problem.objects.get(id=pid)
                data["suggest_problem"].latest_revision = self.get_problem_latest_revision(data["suggest_problem"])
        return data


class ProblemCreate(PolygonBaseMixin, View):
    @staticmethod
    def get_unused_problem():
        revised_probs = set(Revision.objects.values_list("problem_id", flat=True))
        for problem in Problem.objects.all().order_by("id"):
            if not problem.description and not problem.input and not problem.output and not problem.cases and \
                    problem.id not in revised_probs:
                return problem
        return None

    def post(self, request, *args, **kwargs):
        if 'force' in request.GET:
            problem = None
        else:
            problem = self.get_unused_problem()
        if not problem:
            problem = Problem.objects.create()
            problem.title = 'Problem #%d' % problem.id
            problem.alias = 'p%d' % problem.id
            problem.save(update_fields=['title', 'alias'])
        problem.managers.add(request.user)
        revision = Revision.objects.create(problem=problem,
                                           user=self.request.user,
                                           revision=1,
                                           time_limit=problem.time_limit,
                                           memory_limit=problem.memory_limit)
        return redirect(reverse('polygon:revision_update', kwargs={"pk": problem.pk, "rpk": revision.pk}))


class ProblemClone(PolygonBaseMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            n = request.POST['answer']
            if '-' in n:
                contest_id, identifier = n.split('-')
                contest = Contest.objects.get(pk=contest_id)
                if contest.visible and contest.open_problems and (contest.status > 0 or
                                                                      (contest.always_running and contest.public)):
                    problem = contest.contestproblem_set.get(identifier=identifier).problem
                else:
                    raise PermissionError
            else:
                problem = Problem.objects.get(pk=n)
                if not problem.visible and not is_problem_manager(request.user, problem):
                    raise PermissionError
            new_prob = ProblemCreate.get_unused_problem()
            if not new_prob:
                new_prob = Problem.objects.create()
            new_prob.managers.add(request.user)
            saved_id = new_prob.id
            problem.clone_parent = problem.id
            problem.id = saved_id
            problem.alias = 'p%d' % problem.id
            problem.save()
        except:
            messages.error(request, "Problem does not exist or not available.")
            return redirect(reverse('polygon:problem_list_2'))

        return redirect(reverse('polygon:problem_list_2') + "?exact=%d" % saved_id)


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
        else:
            self.permission = 0

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

    def group_well_ordered(self):
        if not self.revision.enable_group:
            return True
        expect_group_number = 1
        for case in self.revision.cases.all().order_by("case_number"):
            if case.group != expect_group_number:
                if case.group == expect_group_number + 1:
                    expect_group_number += 1
                else:
                    return False
        if expect_group_number != self.revision.group_count:
            return False
        return True

    def case_number_well_ordered(self):
        for idx, case in enumerate(self.revision.cases.all().order_by("case_number"), start=1):
            if case.case_number != idx:
                return False
        return True

    def revision_health_check(self):
        self.errors = []
        self.warnings = []

        if not self.group_well_ordered():
            self.errors.append("Group numbers are NOT well ordered.")
        if not self.case_number_well_ordered():
            self.warnings.append("Case numbers are not perfectly ordered.")
        if not self.revision.active_statement:
            self.errors.append("Must have an active statement.")
        if not (256 <= self.revision.memory_limit <= 4096):
            self.errors.append("Memory limit should be between 256MB and 4GB.")
        if not (500 <= self.revision.time_limit <= 30000):
            self.errors.append("Time limit should be between 500ms and 30 seconds.")
        if not self.revision.time_limit * self.revision.cases.count() <= 900000:
            self.warnings.append("Time limit of all cases exceeds 900 seconds. This brings potential problems that "
                                 "judge requests will timeout.")
        if not self.revision.well_form_policy:
            self.warnings.append("Well form policy is not enabled. This brings potential problems in end-of-line and "
                                 "unexpected spaces. Make sure you want to do this.")

    def init_revision(self, *args, **kwargs):
        self.revision = self.problem.revisions.select_related("active_statement", "active_checker", "active_validator",
                                                              "active_interactor", "user").filter(pk=kwargs['rpk'])
        if len(self.revision) == 0:
            raise Http404("Revision matches not found.")
        else: self.revision = self.revision[0]
        if self.revision.user != self.request.user or self.revision.status != 0:
            self.permission = 1
        self.revision_health_check()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['revision'] = self.revision
        data['revision_errors'] = self.errors
        data['revision_warnings'] = self.warnings
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
        data['level_select'] = self.problem._meta.get_field('level').choices
        return data

    @transaction.atomic()
    def post(self, request, pk):
        self.problem.alias = request.POST['alias']
        self.problem.source = request.POST['source']
        self.problem.level = request.POST['level']
        my_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        self.problem.managers.clear()
        for key in my_set:
            self.problem.managers.add(User.objects.get(pk=key))
        self.problem.save()
        return redirect(self.request.path)
