import json

from django.shortcuts import HttpResponseRedirect, reverse, HttpResponse
from django.views.generic import CreateView
from django.views.generic.list import ListView, View
from django.db import transaction
from django.db.models import Q

from backstage.log.forms import LogForm
from backstage.models import UpdateLog
from ..base_views import BaseBackstageMixin, BaseCreateView


class UpdateLogList(BaseBackstageMixin, ListView):
    template_name = 'backstage/log/list.jinja2'
    context_object_name = 'log_list'
    queryset = UpdateLog.objects.select_related("created_by").order_by("-pk")


class UpdateLogCreate(BaseCreateView):
    form_class = LogForm
    template_name = 'backstage/log/add.jinja2'

    def get_redirect_url(self, instance):
        return reverse('backstage:log')


class UpdateLogDelete(BaseBackstageMixin, View):
    @transaction.atomic()
    def post(self, request, pk):
        instance = UpdateLog.objects.get(pk=pk)
        instance.delete()
        return HttpResponse()
