from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from .forms import ServerEditForm
from dispatcher.models import Server

from ..base_views import BaseCreateView, BaseUpdateView


class ServerCreate(BaseCreateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_add.html'

    def get_redirect_url(self, instance):
        return reverse('backstage:server')


class ServerUpdate(BaseUpdateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_edit.html'
    queryset = Server.objects.all()


class ServerList(ListView):
    template_name = 'backstage/server/server.html'
    queryset = Server.objects.all()
    paginate_by = 5
    context_object_name = 'server_list'
