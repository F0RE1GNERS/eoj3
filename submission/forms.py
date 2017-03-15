from django import forms
from .models import Submission


class SubmitForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code', 'lang']
