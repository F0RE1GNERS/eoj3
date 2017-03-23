from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib import messages

from .forms import ServerEditForm
from dispatcher.models import Server

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


class ServerRefresh(BaseBackstageMixin, View):
    def get(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.serverproblemstatus_set.all().delete()
        messages.success(request, "Server status has been refreshed.")
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerDelete(BaseBackstageMixin, View):
    def get(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.delete()
        messages.success(request, "Server <strong>%s</strong> is successfully removed." % server.name)
        return HttpResponseRedirect(reverse('backstage:server'))
