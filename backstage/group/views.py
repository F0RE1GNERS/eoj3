from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.views import View
from django.utils.decorators import method_decorator

from .forms import GroupEditForm
from group.models import Group, GroupMembership
from account.models import User
from utils.models import InvitationCode
from utils.invitation import generate

from ..base_views import BaseCreateView, BaseUpdateView


class GroupManage(View):
    template_name = 'backstage/group/group_manage.jinja2'

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
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))


class GroupCreate(BaseCreateView):
    form_class = GroupEditForm
    template_name = 'backstage/group/group_add.jinja2'

    def get_redirect_url(self, instance):
        return reverse('backstage:group_manage', kwargs={'pk': instance.pk})


class GroupUpdate(BaseUpdateView):
    form_class = GroupEditForm
    template_name = 'backstage/group/group_edit.jinja2'
    queryset = Group.objects.all()


@method_decorator(login_required(), name='dispatch')
class GroupList(ListView):
    template_name = 'backstage/group/group.jinja2'
    queryset = Group.objects.all()
    paginate_by = 20
    context_object_name = 'group_list'


@login_required()
def group_member_delete(request, membership_pk):
    membership = GroupMembership.objects.get(pk=membership_pk)
    membership.delete()
    messages.success(request, "User <strong>%s</strong> is successfully removed from group." % membership.user.username)
    return HttpResponseRedirect(reverse('backstage:group_manage', kwargs={'pk': membership.group.pk}))
