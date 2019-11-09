from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from polygon.models import Statement
from polygon.problem2.forms import StatementUpdateForm
from polygon.problem2.views.base import ProblemRevisionMixin


class StatementList(ProblemRevisionMixin, ListView):
  template_name = 'polygon/problem2/statement/list.jinja2'
  context_object_name = 'statement_list'
  polygon_title = "题面"

  def get_queryset(self):
    return self.revision.statements.all()


class RevisionStatementMixin(ProblemRevisionMixin):
  model_class = Statement

  def init_revision(self, *args, **kwargs):
    super().init_revision(*args, **kwargs)
    if not self.verify_belong_to_revision(kwargs['spk']):
      raise Http404("No statement found matching the query")
    self.statement = Statement.objects.get(pk=kwargs['spk'])


class StatementCreateView(ProblemRevisionMixin, CreateView):
  form_class = StatementUpdateForm
  template_name = 'polygon/problem2/simple_form.jinja2'
  polygon_title = "创建题面"

  def get_success_url(self):
    return reverse('polygon:revision_statement', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

  def form_valid(self, form):
    with transaction.atomic():
      form.instance.create_time = datetime.now()
      self.object = form.save()
      self.revision.statements.add(self.object)
      if self.revision.statements.count() == 1:
        self.revision.active_statement = self.object
        self.revision.save(update_fields=["active_statement_id"])
    return redirect(self.get_success_url())


class StatementUpdateView(RevisionStatementMixin, UpdateView):
  form_class = StatementUpdateForm
  template_name = 'polygon/problem2/simple_form.jinja2'
  polygon_title = "更新题面"

  def get_success_url(self):
    return reverse('polygon:revision_statement_preview', kwargs={'pk': self.problem.id, 'rpk': self.revision.id,
                                                                 'spk': self.statement.id})

  def get_object(self, queryset=None):
    return self.statement

  def form_valid(self, form):
    with transaction.atomic():
      self.revision.statements.remove(self.object)
      is_active = self.revision.active_statement == self.object
      form.instance.parent_id = form.instance.pk
      form.instance.pk = None
      self.object = form.save()
      if is_active:
        self.revision.active_statement = self.object
        self.revision.save(update_fields=["active_statement_id"])
      self.revision.statements.add(self.object)
    return redirect(self.get_success_url())


class StatementActivateView(ProblemRevisionMixin, View):
  def post(self, *args, **kwargs):
    try:
      statement = self.revision.statements.get(pk=self.kwargs['spk'])
      self.revision.active_statement = statement
      self.revision.save(update_fields=["active_statement_id"])
      return redirect(reverse('polygon:revision_statement', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
    except Statement.DoesNotExist:
      raise Http404("No statements found matching the query")


class StatementDeleteView(ProblemRevisionMixin, View):
  def post(self, request, *args, **kwargs):
    try:
      object = self.revision.statements.get(pk=kwargs['spk'])
      self.revision.statements.remove(object)
      return redirect(reverse('polygon:revision_statement', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
    except Statement.DoesNotExist:
      raise Http404("No statements found matching the query")


class StatementPreview(RevisionStatementMixin, TemplateView):
  template_name = 'polygon/problem2/statement/preview.jinja2'
  polygon_title = "题面预览"

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data["statement"] = self.statement
    data["samples"] = []
    for case in self.revision.cases.filter(in_samples=True).order_by("case_number"):
      data["samples"].append((case.input_file.read().decode(), case.output_file.read().decode()))
    return data
