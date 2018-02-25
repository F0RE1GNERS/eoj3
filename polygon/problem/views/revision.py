from datetime import datetime

from django.db.models import Max
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from polygon.models import Revision
from polygon.problem.forms import RevisionUpdateForm
from polygon.problem.views.base import ProblemRevisionMixin, PolygonProblemMixin


class RevisionCreateView(PolygonProblemMixin, View):
    """
    Directly create a revision from an online problem
    """

    def post(self, *args, **kwargs):
        if self.problem.revisions.all().count():
            revision_num = self.problem.revisions.all().aggregate(Max("revision")) + 1
        else: revision_num = 1
        revision = Revision.objects.create(problem=self.problem,
                                           user=self.request.user,
                                           revision=revision_num,
                                           time_limit=self.problem.time_limit,
                                           memory_limit=self.problem.memory_limit)
        if self.problem.description or self.problem.input or self.problem.output or self.problem.hint:
            statement = revision.statements.create(description=self.problem.description,
                                                   input=self.problem.input,
                                                   output=self.problem.output,
                                                   hint=self.problem.hint,
                                                   title=self.problem.title,
                                                   create_time=datetime.now())
            revision.active_statement = statement

        return redirect(self.request.path)


class RevisionForkView(ProblemRevisionMixin, View):
    """
    Fork a previous revision into a new one
    """

    def post(self, *args, **kwargs):
        self.revision.parent_id = self.revision.id
        self.revision.id = None
        self.revision.save()
        self.kwargs.update(rpk=self.revision.id)
        return redirect(reverse('polygon:revision_update', kwargs=self.kwargs))


class RevisionUpdateView(ProblemRevisionMixin, UpdateView):
    form_class = RevisionUpdateForm
    template_name = 'polygon/problem/revision/update.jinja2'

    def get_object(self, queryset=None):
        return self.revision

    def get_success_url(self):
        return self.request.path

    def get_context_data(self, **kwargs):
        """
        Index page of revision
        """
        data = super().get_context_data(**kwargs)
        data["revision_list"] = self.problem.revisions.select_related("user").all()
        pk_to_revision = {revision.pk: revision.revision for revision in data["revision_list"]}
        for revision in data["revision_list"]:
            revision.based_on = pk_to_revision.get(revision.parent_id)
        return data


class RevisionConfirmView(ProblemRevisionMixin, UpdateView):
    pass
