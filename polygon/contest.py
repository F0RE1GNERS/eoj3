import json

from .forms import ContestEditForm
from contest.models import Contest, ContestProblem
from .views import PolygonBaseMixin, response_ok
from django.views.generic.edit import UpdateView
from django.views.generic import ListView, View, TemplateView
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from account.permissions import is_admin_or_root
from account.models import User
from problem.statistics import (
    get_problem_accept_count, get_problem_accept_ratio, get_problem_all_count, get_problem_all_user_count,
    get_problem_accept_user_count, get_problem_accept_user_ratio
)
from django.shortcuts import get_object_or_404, reverse, redirect, HttpResponse
from django.db import transaction


def reorder_contest_problem_identifiers(contest: Contest):
    with transaction.atomic():
        problems = contest.contestproblem_set.select_for_update().order_by('identifier').all()
        if problems.count() > 26:
            for index, problem in enumerate(problems, start=1):
                problem.identifier = str(1000 + index)
                problem.save(update_fields=['identifier'])
        else:
            for index, problem in enumerate(problems, start=0):
                problem.identifier = chr(ord('A') + index)
                problem.save(update_fields=['identifier'])


class ContestList(PolygonBaseMixin, ListView):
    template_name = 'polygon/contest_list.jinja2'
    context_object_name = 'contest_list'

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            return Contest.objects.all()
        else:
            return self.request.user.managing_contests.all()


class PolygonContestMixin(TemplateResponseMixin, ContextMixin, PolygonBaseMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('pk'))
        return super(PolygonContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_admin_or_root(self.request.user) and not self.contest.manager.filter(user=self.request.user).exists():
            return False
        return super(PolygonContestMixin, self).test_func()

    def get_context_data(self, **kwargs):
        data = super(PolygonContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        return data


class ContestEdit(PolygonContestMixin, UpdateView):

    form_class = ContestEditForm
    template_name = 'polygon/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def get_context_data(self, **kwargs):
        data = super(ContestEdit, self).get_context_data(**kwargs)
        data['admin_list'] = self.contest.manager.all()
        return data

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.allowed_lang = ','.join(form.cleaned_data['allowed_lang'])
        instance.save()
        return redirect(self.request.path)


class ContestCreate(PolygonBaseMixin, View):

    def post(self, request):
        """
        It is actually "repository create"
        named "session create" for convenience
        """
        if request.method == 'POST':
            contest = Contest.objects.create(title='Contest')
            contest.title = 'Contest #%d' % contest.id
            contest.save(update_fields=['title'])
            return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(contest.id)}))


class ContestToggleVisible(PolygonContestMixin, View):

    def post(self, request, pk):
        self.contest.visible = request.POST.get('checked') == 'true'
        self.contest.save(update_fields=['visible'])
        return response_ok()


class ContestAccessManage(PolygonContestMixin, View):

    def post(self, request, pk):
        upload_permission_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        for record in self.contest.manager.all():
            if record.id in upload_permission_set:
                upload_permission_set.remove(record.id)
            else:
                record.delete()
        for key in upload_permission_set:
            self.contest.manager.add(User.objects.get(pk=key))
        return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))


class ContestProblemManage(PolygonContestMixin, TemplateView):

    template_name = 'polygon/contest_problem.jinja2'

    def get(self, request, *args, **kwargs):
        if 'data' in request.GET:
            problems = self.contest.contestproblem_set.select_related('problem').all()
            data = []
            SUB_FIELDS = ["title", "id"]
            STATISTIC_FIELDS = [
                ('ac1', get_problem_accept_count),
                ('ac2', get_problem_accept_user_count),
                ('tot1', get_problem_all_count),
                ('tot2', get_problem_all_user_count),
                ('ratio1', get_problem_accept_ratio),
                ('ratio2', get_problem_accept_user_ratio),
            ]
            for problem in problems:
                d = {k: getattr(problem.problem, k) for k in SUB_FIELDS}
                d.update(pid=problem.id, identifier=problem.identifier)
                d.update({k: v(problem.problem_id, self.contest.id) for k, v in STATISTIC_FIELDS})
                data.append(d)
            data.sort(key=lambda x: x['identifier'])
            return HttpResponse(json.dumps(data))
        return super(ContestProblemManage, self).get(request, *args, **kwargs)



class ContestProblemCreate(PolygonContestMixin, View):

    def post(self, request, pk):
        def get_next_identifier(identifiers):
            from collections import deque
            q = deque()
            q.append('')
            while q:
                u = q.popleft()
                if u and u not in identifiers:
                    return u
                for i in range(ord('A'), ord('Z') + 1):
                    q.append(u + chr(i))

        problems = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['problems'].split(','))))
        for problem in problems:
            if self.contest.contestproblem_set.objects.filter(problem_id=problem).exists():
                continue
            identifier = get_next_identifier([x.identifier for x in self.contest.contestproblem_set.all()])
            self.contest.contestproblem_set.create(problem_id=problem, identifier=identifier)
        reorder_contest_problem_identifiers(self.contest)
        return response_ok()