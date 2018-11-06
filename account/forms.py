from django import forms

from utils.rsa_gen import get_public_key, get_keys, decryptRSA
from utils.site_settings import is_festival
from .models import User
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from captcha.fields import CaptchaField
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _


def compare_string(a, b):
    try:
        return ''.join(a.split()) == ''.join(b.split())
    except:
        return False


class LoginForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super(LoginForm, self).__init__(request, *args, **kwargs)
        self.fields['username'].label = '用户名'
        self.fields['password'].label = '密码'
        self.fields['public_key'].initial = get_public_key()

    captcha = CaptchaField(label="小学数学题")
    remember_me = forms.BooleanField(required=False)
    public_key = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        priv, pub = get_keys()
        if not compare_string(self.cleaned_data.get("public_key"), pub.decode()):
            raise forms.ValidationError("公钥失效。尝试刷新。")
        try:
            self.cleaned_data["password"] = decryptRSA(self.cleaned_data["password"], priv).decode()
        except:
            raise forms.ValidationError("密码解密失败。尝试刷新。")
        return super().clean()



class RegisterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'username']
        help_texts = {
            'email': '电子邮箱可以修改。',
            'username': '用户名可以有偿修改。'
        }
        error_messages = {
            'username': {
                'require': '用户名是必填的。'
            },
            'email': {
                'require': '电子邮箱是必填的。'
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['public_key'].initial = get_public_key()

    def create(self):
        instance = self.save(commit=False)
        instance.set_password(self.cleaned_data.get('password'))
        if not User.objects.exists():
            instance.is_superuser = True
        instance.save()
        return instance

    def clean(self):
        data = super(RegisterForm, self).clean()

        priv, pub = get_keys()
        if not compare_string(data.get("public_key"), pub.decode()):
            raise forms.ValidationError("公钥失效。尝试刷新。")
        try:
            data["password"] = decryptRSA(data["password"], priv).decode()
            data["repeat_password"] = decryptRSA(data["repeat_password"], priv).decode()
        except:
            raise forms.ValidationError("密码解密失败。尝试刷新。")

        if data.get('password') != data.get('repeat_password'):
            self.add_error('repeat_password', forms.ValidationError("确认密码和密码不相符。", code='invalid'))
        return data

    password = forms.CharField(help_text="密码长度最少是 6。",
                               widget=forms.PasswordInput,
                               min_length=6,
                               required=True,
                               error_messages={
                                   'min_length': "密码太短。",
                                   'require': "密码是必填的。",
                               },
                               label="密码")
    repeat_password = forms.CharField(widget=forms.PasswordInput,
                                      required=True,
                                      error_messages={
                                          'require': "请确认密码。"
                                      },
                                      label="确认密码")
    public_key = forms.CharField(widget=forms.HiddenInput())
    captcha = CaptchaField(label="小学数学题")


class MyPasswordChangeForm(PasswordChangeForm):
    new_password1 = forms.CharField(
        label="新密码",
        widget=forms.PasswordInput,
        strip=False,
        help_text='',
    )


class MySetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="新密码",
        widget=forms.PasswordInput,
        strip=False,
        help_text='',
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'name', 'student_id', 'school', 'motto', 'magic', 'avatar', 'email_subscription', 'show_tags']
        help_texts = {
            'magic': '试试看呢？'
        }
        error_messages = {
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_festival():
            self.fields.pop('magic')

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']
        if avatar.size > 2 * 1048576:
            raise forms.ValidationError("文件大小不超过 2MB。")
        return avatar


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['show_tags', 'preferred_lang']


class FeedbackForm(forms.Form):

    title = forms.CharField(label='标题', max_length=60, help_text="你遇到了什么问题")
    content = forms.CharField(label="内容", widget=forms.Textarea, help_text="如果是 bug，请指出具体的情形；如果是改进建议，也欢迎提出。")
