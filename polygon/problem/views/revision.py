from django.db.models import Max
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView
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
                                           memory_limit=self.problem.memory_limit,
                                           alias=self.problem.alias)
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
        return redirect(reverse('polygon:revision_view', kwargs=self.kwargs))


class RevisionUpdateView(ProblemRevisionMixin, UpdateView):
    """
    Revision update form
    """
    form_class = RevisionUpdateForm

    def get_object(self, queryset=None):
        return self.revision

    def get_success_url(self):
        return self.request.path
