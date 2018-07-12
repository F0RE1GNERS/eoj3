from django import forms

from backstage.models import UpdateLog


class LogForm(forms.ModelForm):
    class Meta:
        model = UpdateLog
        fields = ['log_type', 'priority', 'is_about_polygon', 'content']
