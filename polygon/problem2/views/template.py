from datetime import datetime

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from polygon.models import Template
from polygon.problem2.forms import TemplateUpdateForm
from polygon.problem2.views.base import ProblemRevisionMixin
from utils.language import transform_code_to_html


class TemplateList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem2/template/list.jinja2'
    context_object_name = 'template_list'
    polygon_title = "模板"

    def get_queryset(self):
        return self.revision.templates.all()


class RevisionTemplateMixin(ProblemRevisionMixin):
    model_class = Template

    def init_revision(self, *args, **kwargs):
        super().init_revision(*args, **kwargs)
        if not self.verify_belong_to_revision(kwargs['tpk']):
            raise Http404("No template found matching the query")
        self.template = Template.objects.get(pk=kwargs['tpk'])


class TemplateCreateView(ProblemRevisionMixin, CreateView):
    form_class = TemplateUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'
    polygon_title = "创建模板"

    def get_success_url(self):
        return reverse('polygon:revision_template', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.create_time = datetime.now()
            self.object = form.save()
            self.revision.templates.add(self.object)
        return redirect(self.get_success_url())


class TemplateUpdateView(RevisionTemplateMixin, UpdateView):
    form_class = TemplateUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'
    polygon_title = "更新模板"

    def get_success_url(self):
        return reverse('polygon:revision_template_preview', kwargs={'pk': self.problem.id, 'rpk': self.revision.id,
                                                                    'tpk': self.template.id})

    def get_object(self, queryset=None):
        return self.template

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.templates.remove(self.object)
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            self.revision.templates.add(self.object)
        return redirect(self.get_success_url())


class TemplateDeleteView(ProblemRevisionMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            object = self.revision.templates.get(pk=kwargs['tpk'])
            self.revision.templates.remove(object)
            return redirect(reverse('polygon:revision_template', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
        except Template.DoesNotExist:
            raise Http404("No templates found matching the query")


class TemplatePreview(RevisionTemplateMixin, TemplateView):
    template_name = 'polygon/problem2/template/preview.jinja2'
    polygon_title = "模板预览"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        self.template.template_code_as_html = transform_code_to_html(self.template.template_code,
                                                                     self.template.language)
        self.template.grader_code_as_html = transform_code_to_html(self.template.grader_code,
                                                                   self.template.language)
        data["template"] = self.template
        return data
