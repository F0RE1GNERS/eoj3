import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import HttpResponseRedirect, HttpResponse, reverse, get_object_or_404, redirect
from django.views.generic import TemplateView
from django.views.generic import View
from django.views.generic.list import ListView

from .forms import ProblemEditForm
from dispatcher.tasks import ProblemRejudgeThread
from problem.models import Problem
from submission.models import Submission
from ..base_views import BaseBackstageMixin, BaseUpdateView


class ProblemList(BaseBackstageMixin, ListView):
    template_name = 'backstage/problem.jinja2'
    queryset = Problem.objects.order_by("-update_time").all()
    paginate_by = 250
    context_object_name = 'problem_list'


class ProblemVisibleSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(pk=pk)
            problem.visible = True if not problem.visible else False
            problem.save(update_fields=["visible"])
        return HttpResponse(json.dumps({'result': 'success'}))


class ProblemTagList(BaseBackstageMixin, ListView):
    template_name = 'backstage/tags.jinja2'
    queryset = Problem.tags.all()
    context_object_name = 'tag_list'
