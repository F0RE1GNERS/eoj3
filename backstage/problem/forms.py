from django import forms
from problem.models import Problem


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'time_limit', 'sum_time_limit', 'memory_limit', 'description', 'input', 'output',
                  'sample', 'hint', 'visible']
        error_messages = {
        }
