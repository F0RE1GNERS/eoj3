from django import forms
from .models import User


class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
    password = forms.CharField(widget=forms.PasswordInput,
                               min_length=6,
                               error_messages={
                                   'min_length': "Your password is too short."
                               }
                               )