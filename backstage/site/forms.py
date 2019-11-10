from django import forms

from utils.site_settings import SiteSettings


class SiteSettingsForm(forms.ModelForm):
  class Meta:
    model = SiteSettings
    fields = '__all__'
