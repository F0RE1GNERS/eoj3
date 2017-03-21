from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.views import View
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import IntegrityError

from .forms import ContestEditForm
from contest.models import Contest, ContestProblem
from problem.models import Problem
from group.models import Group
from contest.tasks import update_contest

from ..base_views import BaseCreateView, BaseUpdateView


def get_formatted_time():
    return timezone.now().strftime("%Y-%m-%d 00:00")


class ContestManage(View):
    template_name = 'backstage/contest/contest_manage.jinja2'

    @staticmethod
    def get_context_data(**kwargs):
        contest = Contest.objects.get(**kwargs)
        contest_problem_list = ContestProblem.objects.filter(contest=contest).all()
        group_list = contest.groups.all()
        return dict(contest=contest, contest_problem_list=contest_problem_list, group_list=group_list)

    def post(self, request, **kwargs):
        group_pk = request.POST.get('group')
        contest = Contest.objects.get(**kwargs)
        if group_pk:
            contest.groups.add(Group.objects.get(pk=group_pk))
        update_contest(contest)
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))


class ContestCreate(BaseCreateView):
    initial = {'start_time': get_formatted_time(), 'end_time': get_formatted_time()}
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_add.jinja2'

    def get_redirect_url(self, instance):
        return self.request.POST.get('next', self.request.path)

    def post_create(self, instance):
        super(ContestCreate, self).post_create(instance)
        update_contest(instance)


class ContestUpdate(BaseUpdateView):
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def post_update(self, instance):
        super(ContestUpdate, self).post_update(instance)
        update_contest(instance)


@method_decorator(login_required(), name='dispatch')
class ContestList(ListView):
    template_name = 'backstage/contest/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 20
    context_object_name = 'contest_list'


def contest_problem_create(request, contest_pk):
    if request.method == 'POST':
        try:
            contest = Contest.objects.get(pk=contest_pk)
            problem_pk = request.POST['problem']
            identifier = request.POST['identifier']
            if problem_pk == '':
                raise KeyError
            ContestProblem.objects.create(contest=contest, problem=Problem.objects.get(pk=problem_pk),
                                          identifier=identifier)
            update_contest(contest)
        except (ValueError, KeyError, Contest.DoesNotExist, Problem.DoesNotExist):
            messages.error(request, 'Contest problem or tag might be illegal.')
        except IntegrityError:
            messages.error(request, 'Problem and ID must be unique.')
        return HttpResponseRedirect(request.POST['next'])


def contest_problem_delete(request, contest_pk, contest_problem_pk):
    contest = Contest.objects.get(pk=contest_pk)
    contest.contestproblem_set.get(pk=contest_problem_pk).delete()
    update_contest(contest)
    messages.success(request, "This problem has been successfully deleted.")
    return HttpResponseRedirect(reverse('backstage:contest_manage', kwargs={'pk': contest_pk}))
