from django import forms
from tagging.models import Tag

from problem.models import Skill, Problem, TagInfo
from utils.multiple_choice_field import CommaSeparatedMultipleChoiceField


class SkillEditForm(forms.ModelForm):
    class Meta:
        model = Skill
        exclude = ['parent_id', 'problem_list']

    problem_list = CommaSeparatedMultipleChoiceField(required=False)
    parent = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        skill = self.instance
        self.fields['problem_list'].initial = skill.problem_list
        self.fields['problem_list'].choices = [(problem.pk, str(problem)) for problem in Problem.objects.only("title").all()]
        self.fields['parent'].initial = skill.parent_id
        self.fields['parent'].choices = [(-1, 'None')] + [(skill.pk, skill.name) for skill in Skill.objects.exclude(pk=self.instance.pk).exclude(parent_id=self.instance.pk)]


class SetSourceForm(forms.Form):
    id_start = forms.IntegerField()
    id_end = forms.IntegerField()
    source = forms.CharField()


class TagEditForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']

    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'markdown'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'taginfo'):
            self.fields['description'].initial = self.instance.taginfo.description

    def save(self, commit=True):
        tag = super().save(commit=commit)
        tag_info, _ = TagInfo.objects.get_or_create(tag=tag)
        tag_info.description = self.cleaned_data['description']
        tag_info.save(update_fields=['description'])
