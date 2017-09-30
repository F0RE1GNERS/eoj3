from captcha.fields import CaptchaField
from django import forms


class MigrateForm(forms.Form):
    is_new = forms.ChoiceField(label='Registered at', choices=(
        ('old', 'Registered at Old EOJ before Feb 2017'),
        ('new', 'Registered at New EOJ since May 2017')
    ))
    username = forms.CharField(label='Old username', max_length=224, required=True)
    password = forms.CharField(label='Old password', widget=forms.PasswordInput, max_length=224, required=True)
    captcha = CaptchaField()

