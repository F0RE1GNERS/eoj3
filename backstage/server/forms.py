from django import forms
from dispatcher.models import Server


class ServerEditForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['name', 'ip', 'port', 'token', 'concurrency']
        labels = {
            'ip': 'IP Address'
        }
        help_texts = {
            'name': 'Whatever name you like',
            'ip': 'xxx.xxx.xxx.xxx',
            'token': 'If the server is newly created, this should be "naive".'
        }


class ServerUpdateTokenForm(forms.Form):

    new_password = forms.CharField(min_length=4, max_length=128, label='New Password')

