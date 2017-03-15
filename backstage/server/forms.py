from django import forms
from dispatcher.models import Server


class ServerEditForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['name', 'ip', 'port', 'token']
        labels = {
            'ip': 'IP Address'
        }
