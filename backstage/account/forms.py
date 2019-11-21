from django import forms

from account.models import School


class SchoolForm(forms.ModelForm):
  class Meta:
    model = School
    fields = "__all__"
