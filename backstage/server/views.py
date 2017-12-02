import threading
from datetime import datetime

from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import HttpResponseRedirect, reverse
from django.views.generic import FormView
from django.views.generic import View
from django.views.generic.list import ListView

from dispatcher.models import Server
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
        server = Server.objects.get(pk=pk)
        server.delete()
        messages.success(request, "Server <strong>%s</strong> is successfully removed." % server.name)
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


class ServerSynchronize(BaseBackstageMixin, View):

    def post(self, request, pk):

        def synchronize_func(server):
            count = Problem.objects.all().count()
            for idx, problem in enumerate(Problem.objects.all(), start=1):
                cache.set('server_synchronize_status_detail', '%d / %d' % (idx, count), 60)
                cache.set('server_synchronize_status', idx / count * 100, 60)
                if not upload_problem_to_judge_server(problem, server):
                    return
            server.last_synchronize_time = datetime.now()
            server.save(update_fields=['last_synchronize_time'])

        server = Server.objects.get(pk=pk)
        threading.Thread(target=synchronize_func, args=(server,)).start()
        return HttpResponseRedirect(reverse('backstage:server'))