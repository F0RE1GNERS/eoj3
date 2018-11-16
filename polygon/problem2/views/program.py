from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from polygon.models import Program
from polygon.problem2.forms import ProgramUpdateForm, ProgramImportForm
from polygon.problem2.views.base import ProblemRevisionMixin
from problem.models import SpecialProgram
from utils.language import transform_code_to_html

ACTIVABLE_PROGRAM_TAGS = ("checker", "interactor", "validator")


class ProgramList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem2/program/list.jinja2'
    context_object_name = 'program_list'
    polygon_title = "程序"

    def get_queryset(self):
        qs = self.revision.programs.all()
        for program in qs:
            program.is_active = False
            for tag in ACTIVABLE_PROGRAM_TAGS:
                if getattr(self.revision, 'active_%s' % tag) == program:
                    program.is_active = True
                    break
        return qs


class RevisionProgramMixin(ProblemRevisionMixin):
    model_class = Program

    def init_revision(self, *args, **kwargs):
        super().init_revision(*args, **kwargs)
        if not self.verify_belong_to_revision(kwargs['ppk']):
            raise Http404("No program found matching the query")
        self.program = Program.objects.get(pk=kwargs['ppk'])



class ProgramCreateView(ProblemRevisionMixin, CreateView):
    form_class = ProgramUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'
    polygon_title = "创建程序"

    def get_success_url(self):
        return reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.create_time = datetime.now()
            self.object = form.save()
            self.revision.programs.add(self.object)
        return redirect(self.get_success_url())


class ProgramUpdateView(RevisionProgramMixin, UpdateView):
    form_class = ProgramUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'
    polygon_title = "更新程序"

    def get_success_url(self):
        return reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        return self.program

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
        return redirect(self.get_success_url())


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


class ProgramDeleteView(ProblemRevisionMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            object = self.revision.programs.get(pk=kwargs['ppk'])
            self.revision.programs.remove(object)
            return redirect(reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
        except Program.DoesNotExist:
            raise Http404("No programs found matching the query")


class ProgramPreview(RevisionProgramMixin, TemplateView):
    template_name = 'polygon/problem2/program/preview.jinja2'
    polygon_title = "程序预览"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["program"] = self.program
        self.program.code_as_html = transform_code_to_html(self.program.code, self.program.lang)
        return data


class ProgramImportView(ProblemRevisionMixin, FormView):
    template_name = 'polygon/problem2/simple_form.jinja2'
    form_class = ProgramImportForm
    polygon_title = "程序导入"

    def get_success_url(self):
        return reverse('polygon:revision_program', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        program = SpecialProgram.objects.get(fingerprint=form.cleaned_data["program"], builtin=True)
        self.revision.programs.create(name=program.filename,
                                      fingerprint=program.fingerprint,
                                      lang=program.lang,
                                      tag=program.category,
                                      create_time=datetime.now(),
                                      code=program.code)
        return redirect(self.get_success_url())

