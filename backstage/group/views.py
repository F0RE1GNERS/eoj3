from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.views import View
from django.utils.decorators import method_decorator

from .forms import GroupEditForm
from group.models import Group, GroupMembership
from account.models import User
from utils.models import InvitationCode
from utils.invitation import generate


class GroupManage(View):
    template_name = 'backstage/group/group_manage.html'

    @staticmethod
    def get_context_data(**kwargs):
        group = Group.objects.get(**kwargs)
        membership_list = GroupMembership.objects.filter(group=group).all()
        code_list = InvitationCode.objects.filter(group_id=group.id).all()
        return dict(group=group, membership_list=membership_list, code_list=code_list)

    def post(self, request, **kwargs):
        group = Group.objects.get(**kwargs)
        username = request.POST.get('username', None)
        number = request.POST.get('number', None)
        comment = request.POST.get('comment', '')
        if username:
            GroupMembership.objects.create(user=User.objects.get(username=username), comment=comment, group=group)
        if number:
            generate(group, number, comment)
        data = self.get_context_data(**kwargs)
        return render(request, self.template_name, data)

    def get(self, request, **kwargs):
        data = self.get_context_data(**kwargs)
        return render(request, self.template_name, data)


@method_decorator(login_required(), name='dispatch')
class GroupCreate(CreateView):
    form_class = GroupEditForm
    template_name = 'backstage/group/group_add.html'

    def get_success_url(self):  # TODO reverse
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
