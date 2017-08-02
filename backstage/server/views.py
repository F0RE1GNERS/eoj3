from django.contrib import messages
from django.shortcuts import HttpResponseRedirect, reverse
from django.views.generic import FormView
from django.views.generic import View
from django.views.generic.list import ListView

from dispatcher.models import Server
from dispatcher.manage import update_token
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


class ServerRefresh(BaseBackstageMixin, View):

    def post(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.serverproblemstatus_set.all().delete()
        messages.success(request, "Server status has been refreshed.")
        return HttpResponseRedirect(reverse('backstage:server'))


class ServerEnableOrDisable(BaseBackstageMixin, View):

    def post(self, request, pk):
        server = Server.objects.get(pk=pk)
        server.enabled = request.POST.get('checked') == 'true'
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
