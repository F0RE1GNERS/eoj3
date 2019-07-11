from django import forms

from paste.models import Paste
from utils.multiple_choice_field import UserSelectMultiple


class PasteForm(forms.ModelForm):
    class Meta:
        model = Paste
        fields = ['code', 'lang', 'public_access', 'expire_after']

    invited_users = UserSelectMultiple(required=False)

    def clean_code(self):
        if len(self.cleaned_data["code"]) > 1048576:
            raise forms.ValidationError("The upper limit for the code is 1MB.")
        return self.cleaned_data["code"]


class AnonymousPasteForm(forms.ModelForm):
    class Meta:
        model = Paste
        fields = ['code', 'lang', 'expire_after']

    def clean_code(self):
        if len(self.cleaned_data["code"]) > 1048576:
            raise forms.ValidationError("The upper limit for the code is 1MB.")
        return self.cleaned_data["code"]
