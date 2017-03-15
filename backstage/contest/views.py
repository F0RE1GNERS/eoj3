from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.views import View
from django.utils.decorators import method_decorator
from django.utils import timezone

from .forms import ContestEditForm
from contest.models import Contest, ContestProblem
from account.models import User

from ..base_views import BaseCreateView, BaseUpdateView


def get_formatted_time():
    return timezone.localtime(timezone.now()).strftime("%Y-%m-%d 00:00")


class ContestManage(View):
    template_name = 'backstage/contest/contest_manage.html'

    @staticmethod
    def get_context_data(**kwargs):
        contest = Contest.objects.get(**kwargs)
        contest_problem_list = ContestProblem.objects.filter(contest=contest).all()
        group_list = contest.groups.all()
        return dict(contest=contest, contest_problem_list=contest_problem_list, group_list=group_list)

    def post(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))


class ContestCreate(BaseCreateView):
    initial = {'start_time': get_formatted_time(), 'end_time': get_formatted_time()}
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_add.html'

    def get_redirect_url(self, instance):
        return self.request.path  # TODO


class ContestUpdate(BaseUpdateView):
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_edit.html'
    queryset = Contest.objects.all()


@method_decorator(login_required(), name='dispatch')
class ContestList(ListView):
    template_name = 'backstage/contest/contest.html'
    queryset = Contest.objects.all()
    paginate_by = 20
    context_object_name = 'contest_list'


