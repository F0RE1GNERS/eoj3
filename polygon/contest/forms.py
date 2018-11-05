from django import forms

from contest.models import Contest
from utils.language import LANG_CHOICE
from utils.multiple_choice_field import CommaSeparatedMultipleChoiceField


class ContestEditForm(forms.ModelForm):
    class Meta:
        model = Contest
        exclude = ['problems', 'participants', "managers", "freeze_time", "freeze",
                   'standings_update_time', 'allowed_lang', 'authors', 'volunteers']
        help_texts = {
            'start_time': 'YYYY-MM-DD --:--(:--)',
            'end_time': 'YYYY-MM-DD --:--(:--)',
            'freeze_time': 'YYYY-MM-DD --:--(:--)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'markdown'})
        }

    field_order = ['title', 'description', 'allowed_lang', 'contest_type', 'how_long', 'start_time', 'end_time', 'access_level', 'common_status_access_level']
    allowed_lang = CommaSeparatedMultipleChoiceField(choices=LANG_CHOICE)
    how_long = forms.ChoiceField(choices=(
        (3, 'Start time to end time'),
        (1, 'Start time to forever'),
        (2, 'Set the deadline'),
        (0, 'Indefinitely'),
    ))

    def __init__(self, *args, **kwargs):
        super(ContestEditForm, self).__init__(*args, **kwargs)
        contest = self.instance
        self.fields['allowed_lang'].initial = contest.allowed_lang
        how_long = 0
        if self.instance.start_time is not None:
            how_long |= 1
        if self.instance.end_time is not None:
            how_long |= 2
        self.fields['how_long'].initial = how_long

    def clean(self):
        cleaned_data = super(ContestEditForm, self).clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        how_long = int(cleaned_data.get('how_long', 3))
        if not (how_long & 1):
            start_time = None
        if not (how_long & 2):
            end_time = None
        if cleaned_data.get('contest_type') == 0:
            if not start_time or not end_time or (end_time - start_time).total_seconds() < 300 or (end_time - start_time).total_seconds() > 86400 * 14:
                raise forms.ValidationError("A regular round should last longer than 5 minutes and less than 14 days.", code='invalid')
        cleaned_data['start_time'] = start_time
        cleaned_data['end_time'] = end_time
        if cleaned_data.get('freeze'):
            freeze_time = cleaned_data.get('freeze_time')
            if not (start_time <= freeze_time <= end_time):
                raise forms.ValidationError('Freeze time is not legal', code='invalid')
        return cleaned_data
