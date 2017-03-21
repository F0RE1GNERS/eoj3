from django import forms
from contest.models import Contest
from django.utils import timezone


class ContestEditForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = ['title', 'description', 'rule', 'start_time', 'end_time', 'visible', 'public']
        help_texts = {
            'start_time': 'YYYY-MM-DD --:--(:--)',
            'end_time': 'YYYY-MM-DD --:--(:--)',
        }

    def clean(self):
        cleaned_data = super(ContestEditForm, self).clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time >= end_time:
            raise forms.ValidationError("Start time should be earlier than end time.", code='invalid')
        # if start_time <= timezone.now():
        #     raise forms.ValidationError("You cannot create a contest in the past.", code='invalid')
        return cleaned_data
