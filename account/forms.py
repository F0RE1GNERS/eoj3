from django import forms
from .models import User
from django.contrib.auth import authenticate


class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'username']
        help_texts = {
            'email': 'Enter an email',
            'username': 'Username cannot be changed once created'
        }
        error_messages = {
            'username': {
                'require': "Please enter your username.",
            },
            'email': {
                'require': "Please enter a email."
            }
        }

    def create(self):
        instance = self.save(commit=False)
        instance.set_password(self.cleaned_data.get('password'))
        instance.save()
        return instance

    def clean_username(self):
        data = self.cleaned_data.get('username')
        if len(data) < 6:
            raise forms.ValidationError("Username should contain at least 6 characters.")
        return data

    def clean(self):
        data = super(RegisterForm, self).clean()
        if data.get('password') != data.get('repeat_password'):
            self.add_error('repeat_password', forms.ValidationError("Password doesn't match.", code='invalid'))
        return data

    password = forms.CharField(help_text='Length should be at least 6',
                               widget=forms.PasswordInput,
                               min_length=6,
                               required=True,
                               error_messages={
                                   'min_length': "Your password is too short.",
                                   'require': "Please enter a password."
                               })
    repeat_password = forms.CharField(help_text="Please repeat your password",
                                      widget=forms.PasswordInput,
                                      required=True,
                                      error_messages={
                                          'require': 'Please repeat your password'
                                      })


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Username and password don't match.", code='invalid')
        return cleaned_data
