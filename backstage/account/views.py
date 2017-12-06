import json

from django.shortcuts import HttpResponseRedirect, reverse, HttpResponse
from django.views.generic.list import ListView, View
from django.db import transaction
from django.db.models import Q

from account.models import Privilege, User
from ..base_views import BaseBackstageMixin


class AccountList(BaseBackstageMixin, ListView):
    template_name = 'backstage/account/account.jinja2'
    paginate_by = 200
    context_object_name = 'user_list'

    def get_queryset(self):
        queryset = User.objects
        kw = self.request.GET.get('keyword')
        admin = self.request.GET.get('admin')
        if kw:
            q = Q(username__icontains=kw) | Q(email__icontains=kw)
            queryset = queryset.filter(q)
        if admin:
            queryset = queryset.exclude(privilege='user')
        return queryset.order_by("-create_time").all()

    def get_context_data(self, **kwargs):
        data = super(AccountList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        data['admin'] = self.request.GET.get('admin')
        return data


class AccountPrivilegeSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=pk)
            if self.request.user.privilege == Privilege.ROOT:
                if user.privilege == 'user':
                    user.privilege = 'volunteer'
                elif user.privilege == 'volunteer':
                    user.privilege = 'admin'
                elif user.privilege == 'admin':
                    user.privilege = 'user'
            elif self.request.user.privilege == Privilege.ADMIN:
                if user.privilege == 'user':
                    user.privilege = 'volunteer'
                elif user.privilege == 'volunteer':
                    user.privilege = 'user'
            user.save()
        return HttpResponse(json.dumps({'result': 'success'}))


class AccountPasswordChange(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = User.objects.select_for_update().get(pk=pk)
            if request.POST.get('password'):
                instance.set_password(request.POST.get('password'))
            instance.save()
        return HttpResponseRedirect(reverse('backstage:account'))


class AccountPolygonSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = User.objects.select_for_update().get(pk=pk)
            instance.polygon_enabled = not instance.polygon_enabled
            instance.save(update_fields=["polygon_enabled"])
        return HttpResponse()


class AccountActiveSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = User.objects.select_for_update().get(pk=pk)
            instance.is_active = not instance.is_active
            instance.save(update_fields=["is_active"])
        return HttpResponse()