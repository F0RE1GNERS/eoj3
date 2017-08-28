from django import forms
from problem.models import Problem


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'alias', 'time_limit', 'memory_limit', 'description', 'input', 'output',
                  'sample', 'hint', 'source', 'visible']
        error_messages = {
        }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'markdown'}),
            'input': forms.Textarea(attrs={'class': 'markdown'}),
            'output': forms.Textarea(attrs={'class': 'markdown'}),
            'hint': forms.Textarea(attrs={'class': 'markdown'}),
        }

    tags = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(ProblemEditForm, self).__init__(*args, **kwargs)
        new_order = ['title', 'alias', 'time_limit', 'memory_limit', 'description',
                     'input', 'output', 'sample', 'hint', 'tags', 'source', 'visible']
        self.fields = type(self.fields)((k, self.fields[k]) for k in new_order)
        if self.instance:
            self.fields['tags'].initial = ','.join(map(str, self.instance.tags))
