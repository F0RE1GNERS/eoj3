import json

from django.db import transaction
from django.db.models import Q
from django.shortcuts import HttpResponse
from django.views.generic import View
from django.views.generic.list import ListView
from rest_framework.response import Response
from rest_framework.views import APIView
from tagging.models import Tag

from problem.models import Problem
from ..base_views import BaseBackstageMixin


class ProblemList(BaseBackstageMixin, ListView):
    template_name = 'backstage/problem.jinja2'
    paginate_by = 250
    context_object_name = 'problem_list'

    def get_queryset(self):
        queryset = Problem.objects
        kw = self.request.GET.get('keyword')
        if kw:
            q = Q(title__icontains=kw) | Q(alias=kw)
            if kw.isdigit():
                q |= Q(pk=kw)
            queryset = queryset.filter(q)
        return queryset.order_by("-update_time").all()


class ProblemVisibleSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(pk=pk)
            problem.visible = True if not problem.visible else False
            problem.save(update_fields=["visible"])
        return HttpResponse(json.dumps({'result': 'success'}))


class ProblemTagList(BaseBackstageMixin, ListView):
    template_name = 'backstage/tags.jinja2'
    queryset = Tag.objects.all()
    context_object_name = 'tag_list'


class ProblemTagCreate(BaseBackstageMixin, APIView):
    def post(self, request, *args, **kwargs):
        name = request.POST['name']
        Tag.objects.create(name=name)
        return Response()


class ProblemTagEdit(BaseBackstageMixin, APIView):
    def post(self, request, *args, **kwargs):
        pk, name = request.POST['pk'], request.POST['name']
        tag = Tag.objects.get(pk=pk)
        tag.name = name
        tag.save(update_fields=["name"])
        return Response()
