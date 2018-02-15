from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView

from polygon.problem.forms import AssetUpdateForm
from polygon.problem.views.base import ProblemRevisionMixin


class AssetList(ProblemRevisionMixin, ListView):
    template_name = 'test.jinja2'
    context_object_name = 'asset_list'

    def get_queryset(self):
        return self.revision.assets.all()


class AssetCreateView(ProblemRevisionMixin, CreateView):
    form_class = AssetUpdateForm

    def get_success_url(self):
        return reverse('polygon:asset_list', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})


class AssetUpdateView(ProblemRevisionMixin, UpdateView):
    form_class = AssetUpdateForm

    def get_success_url(self):
        return reverse('polygon:asset_list', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        return self.revision.assets.get(pk=self.kwargs['apk'])

    def form_valid(self, form):
        self.object.id = None
        return super().form_valid(form)
