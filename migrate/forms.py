from captcha.fields import CaptchaField
from django import forms


class MigrateForm(forms.Form):
    is_new = forms.ChoiceField(label='注册时间', choices=(
        ('old', '在 2017 年二月之前在旧 EOJ 中注册'),
        ('new', '在 2017 年五月之后在新 EOJ 中注册')
    ))
    username = forms.CharField(label='用户名', max_length=224, required=True)
    password = forms.CharField(label='密码', widget=forms.PasswordInput, max_length=224, required=True)
    captcha = CaptchaField(label="小学数学题")
