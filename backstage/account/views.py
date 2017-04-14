from django.shortcuts import HttpResponseRedirect, reverse
from django.views.generic.list import ListView, View
from django.db import transaction

from account.models import Privilege, User
from ..base_views import BaseBackstageMixin

class AccountList(BaseBackstageMixin, ListView):
    template_name = 'backstage/account/account.jinja2'
    queryset = User.objects.all()
    paginate_by = 200
    context_object_name = 'user_list'


class AccountPrivilegeSwitch(BaseBackstageMixin, View):
    def test_func(self):
        return super(AccountPrivilegeSwitch, self).test_func() and self.request.user.privilege == Privilege.ROOT

    def get(self, request, pk):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=pk)
            if user.privilege == 'user':
                user.privilege = 'admin'
            elif user.privilege == 'admin':
                user.privilege = 'user'
            user.save()
        return HttpResponseRedirect(reverse('backstage:account'))


class AccountPasswordChange(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = User.objects.select_for_update().get(pk=pk)
            if request.POST.get('password'):
                instance.set_password(request.POST.get('password'))
            instance.save()
        return HttpResponseRedirect(reverse('backstage:account'))
