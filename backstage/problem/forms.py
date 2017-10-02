from django import forms

from problem.models import Skill, Problem
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
