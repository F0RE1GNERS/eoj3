from django import forms
from .models import User, Privilege
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm


class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'username']
        help_texts = {
            'email': 'Email cannot be changed once created',
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
        if not User.objects.exists():
            instance.privilege = Privilege.ROOT
        instance.save()
        return instance

    def clean_username(self):
        data = self.cleaned_data.get('username')
        if len(data) < 6:
            raise forms.ValidationError("Username should contain at least 6 characters.")
        if '#' in data:
            raise forms.ValidationError("Please do not use # in username.")
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
                                          'require': 'Please repeat your password.'
                                      })


class MyPasswordChangeForm(PasswordChangeForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        strip=False,
        help_text='',
    )


class MySetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        strip=False,
        help_text='',
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'nickname', 'school', 'motto', 'magic', 'avatar']
        help_texts = {
            'magic': 'See what is going to happen!'
        }
        error_messages = {
        }

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']
        if avatar.size > 2 * 1048576:
            raise forms.ValidationError("Image size should not be larger than 2M.")
        return avatar


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['show_tags', 'preferred_lang']


class MigrateForm(forms.Form):
    username = forms.CharField(label='Old username', max_length=224, required=True)
    password = forms.CharField(label='Old password', widget=forms.PasswordInput, max_length=224, required=True)


class FeedbackForm(forms.Form):
    class Meta:
        help_texts = {
            'title': 'What is the problem',
            'content': 'If it is a bug, please identify the time and situation in which you encountered it.'
                       'If you think something is wrong with some problem, feel free to send it in.'
        }
    title = forms.CharField(label='Title', max_length=60, help_text='What is the problem')
    content = forms.CharField(widget=forms.Textarea, help_text='If it is a bug, please identify the time and situation'
                                                               ' in which you encountered it. \nIf you think something '
                                                               'is wrong with some problem, feel free to send it in.')
