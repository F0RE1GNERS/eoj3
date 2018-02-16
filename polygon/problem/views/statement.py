from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
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
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            self.revision.statements.add(self.object)
        return super().form_valid(form)
