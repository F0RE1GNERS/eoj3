from django import forms
from tagging.models import Tag

from polygon.models import Statement, Revision, Program, Case, Asset
from problem.models import Problem
from utils.multiple_choice_field import CommaSeparatedMultipleChoiceField


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'alias', 'time_limit', 'memory_limit', 'description', 'input', 'output',
                  'hint', 'source']
        error_messages = {
        }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'markdown'}),
            'input': forms.Textarea(attrs={'class': 'markdown'}),
            'output': forms.Textarea(attrs={'class': 'markdown'}),
            'hint': forms.Textarea(attrs={'class': 'markdown'}),
        }

    tags = CommaSeparatedMultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(ProblemEditForm, self).__init__(*args, **kwargs)
        new_order = ['title', 'alias', 'time_limit', 'memory_limit', 'description',
                     'input', 'output', 'hint', 'tags', 'source']
        self.fields = type(self.fields)((k, self.fields[k]) for k in new_order)
        if self.instance:
            self.fields['tags'].initial = ','.join(map(str, self.instance.tags))
            self.fields['tags'].choices = [(i, i) for i in Tag.objects.all()]

    def clean(self):
        cleaned_data = super().clean()
        used_tag = []
        if 'tags' in cleaned_data:
            for tag in cleaned_data['tags']:
                if Tag.objects.filter(name=tag).exists():
                    used_tag.append(tag)
        cleaned_data['tags'] = ', '.join(used_tag)
        if ',' not in cleaned_data['tags']:
            cleaned_data['tags'] = "\"%s\"" % cleaned_data['tags']
        return cleaned_data


class RevisionUpdateForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = ['time_limit', 'memory_limit', 'alias', 'well_form_policy']


class StatementUpdateForm(forms.ModelForm):
    class Meta:
        model = Statement
        exclude = ['create_time', 'update_time', 'activated', 'parent_id']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'markdown'}),
            'input': forms.Textarea(attrs={'class': 'markdown'}),
            'output': forms.Textarea(attrs={'class': 'markdown'}),
            'hint': forms.Textarea(attrs={'class': 'markdown'}),
        }


class ProgramUpdateForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["name", "lang", "code", "tag"]


class CaseCreateForm(forms.Form):
    option = forms.ChoiceField(choices=[
        ('batch', 'Upload a zip archive'),
        ('single', 'Upload input file (and output file)'),
        ('gen', 'Generate cases',)])
    input_file = forms.FileField(required=False)
    output_file = forms.FileField(required=False)
    batch_file = forms.FileField(required=False)
    gen_command = forms.CharField(widget=forms.Textarea())


class CaseUpdateForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ["in_samples", "in_pretests", "in_tests", "output_lock",
                  "description", "case_number", "activated"]


class AssetRenameForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ["name"]


class AssetUpdateForm(forms.ModelForm):
    """
    Re-upload a file or create a file
    """
    class Meta:
        model = Asset
        fields = ["name", "file"]
