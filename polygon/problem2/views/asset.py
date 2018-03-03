import os
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView
from shutil import copyfile

from polygon.models import Asset
from polygon.problem2.forms import AssetUpdateForm, AssetRenameForm
from polygon.problem2.views.base import ProblemRevisionMixin
from utils import random_string


def get_random_filename(raw_name, file_path, problem_id):
    _, ext = os.path.splitext(file_path)
    c = os.path.join(str(problem_id), raw_name + "." + random_string(8) + ext)
    dir_in_upload = os.path.join(settings.UPLOAD_DIR, c)
    os.makedirs(os.path.dirname(dir_in_upload), exist_ok=True)
    return dir_in_upload, os.path.join('/upload', c)


class AssetList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem2/asset/list.jinja2'
    context_object_name = 'asset_list'

    def get_queryset(self):
        return self.revision.assets.all()


class AssetCreateView(ProblemRevisionMixin, CreateView):
    form_class = AssetUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_asset', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        form.instance.create_time = datetime.now()
        self.object = form.save()
        self.revision.assets.add(self.object)
        copy_path, self.object.real_path = get_random_filename(self.object.name, self.object.file.path, self.problem.id)
        copyfile(self.object.file.path, copy_path)
        self.object.save(update_fields=["real_path"])
        return redirect(self.get_success_url())


class AssetUpdateView(ProblemRevisionMixin, UpdateView):
    form_class = AssetUpdateForm
    template_name = 'polygon/problem2/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_asset', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        try:
            return self.revision.assets.get(pk=self.kwargs['apk'])
        except Asset.DoesNotExist:
            raise Http404("No assets found matching the query")

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.assets.remove(self.object)
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            copy_path, self.object.real_path = get_random_filename(self.object.name, self.object.file.path, self.problem.id)
            copyfile(self.object.file.path, copy_path)
            self.object.save(update_fields=["real_path"])
            self.revision.assets.add(self.object)
        return redirect(self.get_success_url())


class AssetRenameView(ProblemRevisionMixin, UpdateView):
    form_class = AssetRenameForm
    template_name = 'polygon/problem2/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_asset', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        try:
            return self.revision.assets.get(pk=self.kwargs['apk'])
        except Asset.DoesNotExist:
            raise Http404("No assets found matching the query")

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.assets.remove(self.object)
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            self.revision.assets.add(self.object)
        return redirect(self.get_success_url())


class AssetDeleteView(ProblemRevisionMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            object = self.revision.assets.get(pk=kwargs['apk'])
            self.revision.assets.remove(object)
            return redirect(reverse('polygon:revision_asset', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
        except Asset.DoesNotExist:
            raise Http404("No assets found matching the query")
