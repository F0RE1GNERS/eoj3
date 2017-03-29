from django import forms
from problem.models import Problem


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'time_limit', 'sum_time_limit', 'memory_limit', 'judge', 'description', 'input', 'output',
                  'sample', 'hint', 'source', 'visible']
        error_messages = {
        }

    tags = forms.CharField()

    def save(self, commit=True):
        instance = super(ProblemEditForm, self).save(commit=commit)
        instance.tags = self.cleaned_data['tags']
        return instance

    def __init__(self, *args, **kwargs):
        super(ProblemEditForm, self).__init__(*args, **kwargs)
        new_order = ['title', 'time_limit', 'sum_time_limit', 'memory_limit', 'judge', 'description', 'tags',
                     'input', 'output','sample', 'hint', 'visible']
        self.fields = type(self.fields)((k, self.fields[k]) for k in new_order)
        if self.instance:
            self.fields['tags'].initial = ', '.join(map(str, self.instance.tags))
