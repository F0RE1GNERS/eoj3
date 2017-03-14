from django import forms
from problem.models import Problem


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'description', 'time_limit', 'sum_time_limit', 'memory_limit', 'visible']
        error_messages = {
        }
