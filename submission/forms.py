from django import forms
from django.contrib import messages
from .models import Submission
from submission.models import LANG_CHOICE


class SubmitForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code', 'lang']

    def clean_code(self):
        data = self.cleaned_data['code']
        if len(data) == 0 or len(data) > 65536:
            raise forms.ValidationError('Code should not be empty or contain more than 65536 characters.')
        return data


class ContestSubmitForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        langs = dict(LANG_CHOICE)
        contest_problem_list = kwargs.pop('contest_problem_list')
        contest_allowed_lang = kwargs.pop('contest_allowed_lang')
        super(ContestSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem_identifier'] = forms.ChoiceField(
            choices=[(contest_problem.identifier, "{}. {}".format(contest_problem.identifier, contest_problem.problem.title)) for contest_problem in contest_problem_list])
        self.fields['lang'] = forms.ChoiceField(
            choices=((x, langs[x]) for x in contest_allowed_lang)
        )

    class Meta:
        model = Submission
        fields = ['code', 'lang']

    def clean_code(self):
        data = self.cleaned_data['code']
        if len(data) == 0 or len(data) > 65536:
            raise forms.ValidationError('Code should not be empty or contain more than 65536 characters.')
        return data
