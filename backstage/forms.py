from django import forms
from problem.models import Problem


class ProblemEditForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['title', 'description', 'time_limit', 'sum_time_limit', 'memory_limit']
        error_messages = {
            'title': {
                'require': "Please enter a title.",
            },
            'description': {
                'require': "Please enter a description."
            }
        }

    # def create(self):
    #     instance = self.save(commit=False)
    #     instance.set_password(self.cleaned_data.get('password'))
    #     instance.save()
    #     return instance

    # def clean_username(self):
    #     data = self.cleaned_data.get('username')
    #     if len(data) < 6:
    #         raise forms.ValidationError("Username should contain at least 6 characters.")
    #     return data

    # def clean(self):
    #     data = super(ProblemEditForm, self).clean()
    #     # if data.get('password') != data.get('repeat_password'):
    #     #     self.add_error('repeat_password', forms.ValidationError("Password doesn't match.", code='invalid'))
    #     return data
