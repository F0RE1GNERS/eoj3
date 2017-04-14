from django.shortcuts import render, HttpResponseRedirect, reverse
from utils.models import SiteSettings
from .forms import SiteSettingsForm

from ..base_views import BaseUpdateView


class SiteSettingsUpdate(BaseUpdateView):
    form_class = SiteSettingsForm
    template_name = 'backstage/site/site.jinja2'

    def get_object(self, queryset=None):
        if not SiteSettings.objects.exists():
            SiteSettings.objects.create()
        return SiteSettings.objects.first()

    def get_redirect_url(self, instance):
        return reverse('backstage:site')
