from django import forms

from contest.models import Contest
from utils.language import LANG_CHOICE
from utils.multiple_choice_field import CommaSeparatedMultipleChoiceField


class ContestEditForm(forms.ModelForm):
    class Meta:
        model = Contest
        exclude = ['visible', 'standings_update_time', 'problems', 'participants', "managers",
                   'standings_update_time', 'allowed_lang', 'authors', 'volunteers']
        help_texts = {
            'start_time': 'YYYY-MM-DD --:--(:--)',
            'end_time': 'YYYY-MM-DD --:--(:--)',
            'freeze_time': 'YYYY-MM-DD --:--(:--)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'markdown'})
        }

    field_order = ['title', 'description', 'public', 'allowed_lang', 'start_time', 'end_time']
    allowed_lang = CommaSeparatedMultipleChoiceField(choices=LANG_CHOICE)

    def __init__(self, *args, **kwargs):
        super(ContestEditForm, self).__init__(*args, **kwargs)
        contest = self.instance
        self.fields['allowed_lang'].initial = contest.allowed_lang

    def clean(self):
        cleaned_data = super(ContestEditForm, self).clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if not cleaned_data.get('always_running'):
            if not start_time or not end_time:
                raise forms.ValidationError("For contests not always running, you must assign a start time and an end time", code="invalid")
            if start_time >= end_time:
                raise forms.ValidationError("Start time should be earlier than end time.", code='invalid')
        if cleaned_data.get('freeze'):
            freeze_time = cleaned_data.get('freeze_time')
            if not (start_time <= freeze_time <= end_time):
                raise forms.ValidationError('Freeze time is not legal', code='invalid')
        return cleaned_data
