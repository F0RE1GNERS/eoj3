from django import forms
from .models import User


class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'username']
        help_texts = {
            'email': 'Enter an email',
            'username': 'Username cannot be changed once created'
        }

    password = forms.CharField(help_text='Length should be at least 6',
                               widget=forms.PasswordInput,
                               min_length=6,
                               error_messages={
                                   'min_length': "Your password is too short."
                               })
    repeat_password = forms.CharField(help_text="Please repeat your password",
                                      widget=forms.PasswordInput)
