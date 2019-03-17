from django import forms
from dispatcher.models import Server


class ServerEditForm(forms.ModelForm):
  class Meta:
    model = Server
    fields = ['name', 'ip', 'port', 'token', 'concurrency', 'runtime_multiplier', 'version']


class ServerUpdateTokenForm(forms.Form):
  new_password = forms.CharField(min_length=4, max_length=128, label='New Password')
