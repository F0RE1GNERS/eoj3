from django import forms
from .models import Submission


class SubmitForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['code', 'lang']


class ContestSubmitForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        contest_problem_list = kwargs.pop('contest_problem_list')
        super(ContestSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem_identifier'] = forms.ChoiceField(
            choices=[(contest_problem.identifier, "{} - {}".format(contest_problem.identifier, contest_problem.problem.title)) for contest_problem in contest_problem_list])

    class Meta:
        model = Submission
        fields = ['code', 'lang']

    # problem_identifier = forms.CharField(max_length=12)
