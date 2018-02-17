from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView

from polygon.models import Program
from polygon.problem.forms import ProgramUpdateForm
from polygon.problem.views.base import ProblemRevisionMixin


ACTIVABLE_PROGRAM_TAGS = ("checker", "interactor", "validator")


class ProgramList(ProblemRevisionMixin, ListView):
    template_name = 'test.jinja2'
    context_object_name = 'program_list'

    def get_queryset(self):
        return self.revision.programs.all()


class ProgramCreateView(ProblemRevisionMixin, CreateView):
    form_class = ProgramUpdateForm
    template_name = 'test.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.create_time = datetime.now()
            self.object = form.save()
            self.revision.programs.add(self.object)
        return super().form_valid(form)


class ProgramUpdateView(ProblemRevisionMixin, UpdateView):
    form_class = ProgramUpdateForm

    def get_success_url(self):
        return reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        try:
            return self.revision.programs.get(pk=self.kwargs['ppk'])
        except Program.DoesNotExist:
            raise Http404("No programs found matching the query")

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.programs.remove(self.object)
            old_id = self.object.id
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            for t in ACTIVABLE_PROGRAM_TAGS:
                if getattr(self.revision, 'active_%s_id' % t) == old_id:
                    setattr(self.revision, 'active_%s_id' % t, None)
                    if self.object.tag in ACTIVABLE_PROGRAM_TAGS:
                        setattr(self.revision, 'active_%s_id' % self.object.tag, self.object.id)
                    break
            self.revision.programs.add(self.object)
            self.revision.save()
        return super().form_valid(form)


class ProgramActiveToggleView(ProblemRevisionMixin, View):
    def post(self, *args, **kwargs):
        try:
            program = self.revision.programs.get(pk=self.kwargs['ppk'])
            if program.tag in ACTIVABLE_PROGRAM_TAGS:
                property_name = 'active_%s_id' % program.tag
                if getattr(self.revision, property_name) == program.id:
                    setattr(self.revision, property_name, None)
                else: setattr(self.revision, property_name, program.id)
                self.revision.save(update_fields=[property_name])
            return redirect(reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
        except Program.DoesNotExist:
            raise Http404("No programs found matching the query")
