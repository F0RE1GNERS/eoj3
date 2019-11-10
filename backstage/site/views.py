from django.shortcuts import redirect
from django.views.generic import TemplateView

from utils.site_settings import site_settings_set, SiteSettings
from ..base_views import BaseBackstageMixin


class SiteSettingsUpdate(BaseBackstageMixin, TemplateView):
  template_name = 'backstage/site/site.jinja2'

  def get_context_data(self, **kwargs):
    context = super(SiteSettingsUpdate, self).get_context_data(**kwargs)
    context['site_settings'] = SiteSettings.objects.all()
    return context

  def post(self, request):
    key, value = request.POST['key'], request.POST['value']
    if value == '':
      SiteSettings.objects.filter(key=key).delete()
    else:
      site_settings_set(key, value)
    return redirect(request.POST['next'])
