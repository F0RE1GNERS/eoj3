from django import forms
from group.models import Group


class GroupEditForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']
