from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from .forms import ServerEditForm
from dispatcher.models import Server

@method_decorator(login_required(), name='dispatch')
class ServerCreate(CreateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_add.html'

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        instance.save()
        messages.add_message(self.request, messages.SUCCESS, "Server was successfully added.")
        return HttpResponseRedirect(reverse('backstage:server'))


@method_decorator(login_required(), name='dispatch')
class ServerUpdate(UpdateView):
    form_class = ServerEditForm
    template_name = 'backstage/server/server_edit.html'
    queryset = Server.objects.all()

    def get_success_url(self):
        return self.request.path

    def form_valid(self, form):
        form.save()
        messages.add_message(self.request, messages.SUCCESS, "Your changes have been saved.")
        return HttpResponseRedirect(self.get_success_url())


class ServerList(ListView):
    template_name = 'backstage/server/server.html'
    queryset = Server.objects.all()
    paginate_by = 5
    context_object_name = 'server_list'
