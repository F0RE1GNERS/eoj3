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
    option = forms.ChoiceField(choices=(
        ('text', 'Type in input and output (Recommended for samples)'),
        ('batch', 'Upload a zip archive'),
        ('single', 'Upload input file (and output file)'),
        ('gen', 'Generate cases',)))
    input_file = forms.FileField(required=False)
    output_file = forms.FileField(required=False)
    input_text = forms.CharField(required=False, widget=forms.Textarea())
    output_text = forms.CharField(required=False, widget=forms.Textarea())
    batch_file = forms.FileField(required=False)
    gen_command = forms.CharField(required=False, widget=forms.Textarea())
    in_samples = forms.BooleanField(initial=False, required=False)
    output_lock = forms.BooleanField(initial=False, required=False)
    case_number = forms.IntegerField(initial=0)
    activated = forms.BooleanField(initial=True, required=False)

    def clean(self):
        if self.cleaned_data["option"] == "single" and (
                        self.cleaned_data["input_file"] is None or self.cleaned_data["output_file"] is None):
            raise forms.ValidationError("Input file and output file are required.")
        if self.cleaned_data["option"] == "gen" and not self.cleaned_data["gen_command"]:
            raise forms.ValidationError("Generate Command is required.")
        if self.cleaned_data["option"] == "batch" and self.cleaned_data["batch_file"] is None:
            raise forms.ValidationError("File for batch is required.")


class CaseUpdateInfoForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ["in_samples", "in_pretests", "in_tests", "output_lock",
                  "description", "case_number", "activated"]


class CaseUpdateForm(forms.Form):
    option = forms.ChoiceField(choices=(
        ('file', 'Upload files'),
        ('text', 'Type in textarea')
    ))
    input_file = forms.FileField(required=False)
    output_file = forms.FileField(required=False)
    input_text = forms.CharField(widget=forms.Textarea())
    output_text = forms.CharField(widget=forms.Textarea())

    def clean(self):
        if self.cleaned_data["option"] == "file" and (
                        self.cleaned_data["input_file"] is None or self.cleaned_data["output_file"] is None):
            raise forms.ValidationError("Input file and output file are required.")


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
