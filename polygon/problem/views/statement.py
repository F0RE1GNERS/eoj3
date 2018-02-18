from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView

from polygon.models import Statement
from polygon.problem.forms import StatementUpdateForm
from polygon.problem.views.base import ProblemRevisionMixin


class StatementList(ProblemRevisionMixin, ListView):
    template_name = 'test.jinja2'
    context_object_name = 'statement_list'

    def get_queryset(self):
        return self.revision.statements.all()


class StatementCreateView(ProblemRevisionMixin, CreateView):
    form_class = StatementUpdateForm
    template_name = 'test.jinja2'

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
        return super().form_valid(form)


class StatementUpdateView(ProblemRevisionMixin, UpdateView):
    form_class = StatementUpdateForm

    def get_success_url(self):
        return reverse('polygon:revision_statement', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        try:
            return self.revision.statements.get(pk=self.kwargs['spk'])
        except Statement.DoesNotExist:
            raise Http404("No statements found matching the query")

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
        return super().form_valid(form)


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
        except Statement.DoesNotExist:
            raise Http404("No statements found matching the query")
