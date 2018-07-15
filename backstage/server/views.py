import threading
import traceback
from datetime import datetime

from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.shortcuts import HttpResponseRedirect, reverse, get_object_or_404
from django.views.generic import FormView
from django.views.generic import View
from django.views.generic.list import ListView
from django_q.tasks import async

from dispatcher.models import Server, ServerProblemStatus
from dispatcher.manage import update_token
from problem.models import Problem
from problem.tasks import upload_problem_to_judge_server
from .forms import ServerEditForm, ServerUpdateTokenForm
from ..base_views import BaseCreateView, BaseUpdateView, BaseBackstageMixin


class ServerCreate(BaseCreateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_add.jinja2'

    def get_redirect_url(self, instance):
        return reverse('backstage:server')


class ServerUpdate(BaseUpdateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_edit.jinja2'
    queryset = Server.objects.all()

    def get_redirect_url(self, instance):
        return reverse('backstage:server')


class ServerList(BaseBackstageMixin, ListView):
    template_name = 'backstage/server/server.jinja2'
    queryset = Server.objects.all()
    context_object_name = 'server_list'

    def get_context_data(self, **kwargs):
        data = super(ServerList, self).get_context_data(**kwargs)
        data['server_synchronize_status_detail'] = cache.get('server_synchronize_status_detail', '')
        data['server_synchronize_status'] = cache.get('server_synchronize_status', 0)
        return data


class ServerRefresh(BaseBackstageMixin, View):

    def post(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.serverproblemstatus_set.all().delete()
        messages.success(request, "Server status has been refreshed.")
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerEnableOrDisable(BaseBackstageMixin, View):

    def post(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.enabled = not server.enabled
        server.save(update_fields=['enabled'])
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerDelete(BaseBackstageMixin, View):

    def post(self, request, pk):
        # server = Server.objects.get(pk=pk)
        # server.delete()
        # messages.success(request, "Server <strong>%s</strong> is successfully removed." % server.name)
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerUpdateToken(BaseBackstageMixin, FormView):

    form_class = ServerUpdateTokenForm
    template_name = 'backstage/server/server_edit.jinja2'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            server = Server.objects.get(pk=kwargs.get('pk'))
            if update_token(server, form.cleaned_data['new_password']):
                messages.success(request, 'Token update succeeded.')
                return HttpResponseRedirect(reverse('backstage:server'))
        messages.error(request, 'Update token failed. Please recheck your server status.')
        return HttpResponseRedirect(reverse('backstage:server'))


def synchronize_func(server, problems):
    for idx, problem in enumerate(problems, start=1):
        status, _ = ServerProblemStatus.objects.get_or_create(server=server, problem=problem)
        try:
            upload_problem_to_judge_server(problem, server)
            status.last_status = ''
        except:
            status.last_status = traceback.format_exc()
        status.save()
    server.last_synchronize_time = datetime.now()
    server.save(update_fields=['last_synchronize_time'])


class ServerSynchronize(BaseBackstageMixin, View):

    def post(self, request, pk):

        server = get_object_or_404(Server, pk=pk)
        if request.GET.get("t") == "all":
            problems = Problem.objects.all()
        elif request.GET.get('t', '').isdigit():
            problems = Problem.objects.filter(pk=request.GET['t'])
        else:
            problem_ids = server.serverproblemstatus_set.select_related("problem").\
                filter(last_synchronize__lt=F('problem__update_time')).values_list("problem_id", flat=True)
            problems = Problem.objects.filter(id__in=problem_ids)

        async(synchronize_func, server, list(problems))
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerProblemStatusList(BaseBackstageMixin, ListView):
    template_name = 'backstage/server/server_problem_status.jinja2'
    context_object_name = 'server_problem_status_list'

    def get_queryset(self):
        NEVER = datetime(1990, 1, 1)
        self.server = get_object_or_404(Server, pk=self.kwargs["pk"])
        with transaction.atomic():
            does_not_exist = set(Problem.objects.values_list("id", flat=True)) - \
                             set(ServerProblemStatus.objects.values_list("problem_id", flat=True))
            for problem in does_not_exist:
                ServerProblemStatus.objects.create(server=self.server, problem_id=problem)
            self.server.serverproblemstatus_set.filter(problem_id__in=does_not_exist).update(last_synchronize=NEVER)
        return self.server.serverproblemstatus_set.select_related("problem").only("server_id", "problem_id",
                                                                                  "problem__title", "problem__alias",
                                                                                  "problem__update_time", "last_status",
                                                                                  "last_synchronize").all()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['server'] = self.server
        return data
