from django import forms
from .models import Submission


class SubmitForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code', 'lang']



class ContestSubmitForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code', 'lang']

    problem_identifier = forms.CharField(max_length=12)
