import json
from random import randint

from django.db import transaction
from django.db.models import Q
from django.shortcuts import HttpResponse, redirect
from django.urls import reverse
from django.views.generic import FormView
from django.views.generic import UpdateView
from django.views.generic import View
from django.views.generic.list import ListView
from rest_framework.response import Response
from rest_framework.views import APIView
from tagging.models import Tag, TaggedItem

from backstage.problem.forms import SkillEditForm, SetSourceForm, TagEditForm
from problem.models import Problem, Skill, TagInfo
from ..base_views import BaseBackstageMixin


class ProblemList(BaseBackstageMixin, ListView):
  template_name = 'backstage/problem/problem.jinja2'
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
  template_name = 'backstage/problem/tags.jinja2'
  queryset = Tag.objects.select_related("taginfo").all()
  context_object_name = 'tag_list'

  def get_context_data(self, **kwargs):  # pylint: disable=arguments-differ
    data = super().get_context_data(**kwargs)
    tag_names = {tag.pk: tag.name for tag in Tag.objects.all()}
    for tag in data['tag_list']:
      if hasattr(tag, "taginfo"):
        tag.parent = tag_names.get(tag.taginfo.parent_id, 'N/A')
    data['tag_tree'] = self.get_formatted_tag_data()
    return data

  def search_by_tag(self, dep, tag):
    # return {"name": "...", "children": [] }
    if dep > 10:
      raise ValueError("Max Recursive Limit Exceeded")

    children = TagInfo.objects.filter(parent_id=tag).values_list("tag_id", flat=True)
    if len(children) == 0:
      return {"name": self.tag_names[tag], "value": randint(3000, 5000)}
    else:
      return {"name": self.tag_names[tag], "children": [self.search_by_tag(dep + 1, child) for child in children]}

  def get_formatted_tag_data(self):
    self.tag_names = {tag.pk: tag.name for tag in Tag.objects.all()}
    self.tag_names[-1] = "all"
    return json.dumps(self.search_by_tag(0, -1))


class ProblemTagCreate(BaseBackstageMixin, APIView):
  def post(self, request, *args, **kwargs):
    name = request.POST['name']
    Tag.objects.create(name=name)
    return Response()


class ProblemTagEdit(BaseBackstageMixin, UpdateView):
  form_class = TagEditForm
  template_name = 'backstage/problem/tags_edit.jinja2'
  queryset = Tag.objects.all()

  def get_success_url(self):
    return reverse('backstage:tags')


class ProblemTagDelete(BaseBackstageMixin, APIView):
  def post(self, request, *args, **kwargs):
    tag = Tag.objects.get(pk=kwargs.get('pk'))
    with transaction.atomic():
      if hasattr(tag, 'taginfo'):
        tag.taginfo.delete()
      TaggedItem.objects.filter(tag=tag).delete()
      tag.delete()
    return Response()


class ProblemArchiveList(BaseBackstageMixin, ListView):
  template_name = 'backstage/problem/skill.jinja2'
  queryset = Skill.objects.all()
  context_object_name = 'skill_list'


class ProblemArchiveCreate(BaseBackstageMixin, APIView):
  def post(self, request, *args, **kwargs):
    name = request.POST['name']
    Skill.objects.create(name=name)
    return Response()


class ProblemArchiveEdit(BaseBackstageMixin, UpdateView):
  form_class = SkillEditForm
  template_name = 'backstage/problem/skill_edit.jinja2'
  queryset = Skill.objects.all()

  def form_valid(self, form):
    instance = form.save(commit=False)
    instance.problem_list = ','.join(form.cleaned_data['problem_list'])
    instance.parent_id = form.cleaned_data['parent']
    instance.save()
    return redirect(reverse('backstage:archive'))


class ProblemSourceBatchEdit(BaseBackstageMixin, FormView):
  form_class = SetSourceForm
  template_name = 'backstage/problem/source_edit.jinja2'

  def form_valid(self, form):
    Problem.objects.filter(id__gte=form.cleaned_data["id_start"], id__lte=form.cleaned_data["id_end"]). \
      update(source=form.cleaned_data["source"])
    return redirect(reverse('backstage:problem'))
