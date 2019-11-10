from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.utils.translation import ugettext_lazy as _

from utils.rsa_gen import get_public_key, get_keys, decryptRSA
from utils.site_settings import is_festival
from .models import User


def compare_string(a, b):
  try:
    return ''.join(a.split()) == ''.join(b.split())
  except:
    return False


class LoginForm(AuthenticationForm):
  def __init__(self, request=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
    super(LoginForm, self).__init__(request, *args, **kwargs)
    self.fields['username'].label = "用户名或邮箱"
    self.fields['password'].label = "密码"
    self.fields['public_key'].initial = get_public_key()

  captcha = CaptchaField(label="小学数学题")
  remember_me = forms.BooleanField(label="记住我", required=False)
  public_key = forms.CharField(widget=forms.HiddenInput())

  error_messages = {
    'invalid_login': _(
      "请输入正确的用户名和密码。注意区分大小写。"
    ),
    'inactive': "该账户已失效。",
  }

  def clean(self):
    priv, pub = get_keys()
    if not compare_string(self.cleaned_data.get("public_key"), pub.decode()):
      raise forms.ValidationError("公钥失效，请刷新重试。")
    try:
      self.cleaned_data["password"] = decryptRSA(self.cleaned_data["password"], priv).decode()
    except:
      raise forms.ValidationError("解码失败，请刷新重试。")
    return super().clean()


class RegisterForm(forms.ModelForm):
  class Meta:
    model = User
    fields = ['email', 'username']
    error_messages = {
      'username': {
        'require': "请输入用户名。"
      },
      'email': {
        'require': "请输入邮箱。"
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
      raise forms.ValidationError("公钥失效，请刷新重试。")
    try:
      data["password"] = decryptRSA(data["password"], priv).decode()
      data["repeat_password"] = decryptRSA(data["repeat_password"], priv).decode()
    except:
      raise forms.ValidationError("解码失败，请刷新重试。")

    if data.get('password') != data.get('repeat_password'):
      self.add_error('repeat_password', forms.ValidationError("密码不匹配。", code='invalid'))
    return data

  password = forms.CharField(help_text="至少六位",
                             widget=forms.PasswordInput,
                             min_length=6,
                             required=True,
                             error_messages={
                               'min_length': "密码太短",
                               'require': "请输入密码。"
                             },
                             label=_("Password"))
  repeat_password = forms.CharField(widget=forms.PasswordInput,
                                    required=True,
                                    error_messages={
                                      'require': "请重复输入密码。"
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
    error_messages = {
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not is_festival():
      self.fields.pop('magic')

  def clean_avatar(self):
    avatar = self.cleaned_data['avatar']
    if avatar.size > 2 * 1048576:
      raise forms.ValidationError("图片大小不能超过 2MB。")
    return avatar


class PreferenceForm(forms.ModelForm):
  class Meta:
    model = User
    fields = ['show_tags', 'preferred_lang']


class FeedbackForm(forms.Form):
  title = forms.CharField(label="标题", max_length=60, help_text="你的问题是什么")
  content = forms.CharField(label="内容", widget=forms.Textarea)
