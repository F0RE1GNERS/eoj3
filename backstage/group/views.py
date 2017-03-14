from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from .forms import GroupEditForm
from group.models import Group


def group_edit(request):
    return render(request, 'backstage/group/group_manage.html')


@method_decorator(login_required(), name='dispatch')
class GroupCreate(CreateView):
    form_class = GroupEditForm
    template_name = 'backstage/group/group_add.html'

    def get_success_url(self):  # reverse
        return self.request.path

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        instance.save()
        messages.add_message(self.request, messages.SUCCESS, "Group was successfully added.")
        return HttpResponseRedirect(self.get_success_url())


@method_decorator(login_required(), name='dispatch')
class GroupUpdate(UpdateView):
    form_class = GroupEditForm
    template_name = 'backstage/group/group_edit.html'
    queryset = Group.objects.all()

    def get_success_url(self):
        return self.request.path

    def form_valid(self, form):
        form.save()
        messages.add_message(self.request, messages.SUCCESS, "Your changes have been saved.")
        return HttpResponseRedirect(self.get_success_url())


class GroupList(ListView):
    template_name = 'backstage/group/group.html'
    queryset = Group.objects.all()
    paginate_by = 5
    context_object_name = 'group_list'
