from .forms import ContestEditForm
from contest.models import Contest
from .views import PolygonBaseMixin
from django.views.generic.edit import BaseUpdateView


class ContestEdit(PolygonBaseMixin, BaseUpdateView):

    form_class = ContestEditForm
    template_name = 'polygon/contest_edit.jinja2'
    queryset = Contest.objects.all()


class ContestList(PolygonBaseMixin, ListView):
    template_name = 'polygon/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 100
    context_object_name = 'contest_list'