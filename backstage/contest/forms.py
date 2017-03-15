from django import forms
from contest.models import Contest


class ContestEditForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = ['title', 'description', 'start_time', 'end_time', 'visible']
