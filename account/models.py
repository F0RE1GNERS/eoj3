import json
import html

from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import BaseValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.language import LANG_CHOICE
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill


MAGIC_CHOICE = (
    ('red', '红'),
    ('green', '绿'),
    ('teal', '青'),
    ('blue', '蓝'),
    ('purple', '紫'),
    ('orange', '橙'),
    ('grey', '灰'),
)


class UsernameValidator(UnicodeUsernameValidator):
    regex = r'^[\w.+-]+$'
    message = '有效的用户名应只包含字母、中文、数字和 ./+/-/_。'


class UsernameLengthValidator(BaseValidator):
    message = "用户名应包含至少六个字符。"
    code = 'min_length'

    def compare(self, a, b):
        return a < b

    def clean(self, x):
        try:
            return len(x.encode("GBK"))
        except UnicodeEncodeError:
            return len(x)


class User(AbstractUser):
    username_validators = [UsernameValidator(), UsernameLengthValidator(6)]

    username = models.CharField("用户名", max_length=30, unique=True,
                                validators=username_validators,
                                error_messages={
                                    'unique': "该用户名已经存在。"}
                                )
    email = models.EmailField("电子邮箱", max_length=192, unique=True, error_messages={
        'unique': "该电子邮箱已被使用。"
    })
    school = models.CharField("学校", max_length=64, blank=True)
    name = models.CharField("姓名", max_length=30, blank=True)
    student_id = models.CharField("学号", max_length=30, blank=True)
    magic = models.CharField("魔法", choices=MAGIC_CHOICE, max_length=18, blank=True)
    show_tags = models.BooleanField("展示标签", default=True)
    preferred_lang = models.CharField("语言偏好", choices=LANG_CHOICE, max_length=12, default='cpp')
    motto = models.CharField("励志铭", max_length=192, blank=True)

    avatar = models.ImageField("头像", upload_to='avatar', default='avatar/default.jpg')
    avatar_small = ImageSpecField(source='avatar',
                                  processors=[ResizeToFill(50, 50)],
                                  format='JPEG',
                                  options={'quality': 60})
    avatar_large = ImageSpecField(source='avatar',
                                  processors=[ResizeToFill(500, 500)],
                                  format='JPEG',
                                  options={'quality': 60})
    polygon_enabled = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    username_change_attempt = models.IntegerField(default=0)
    email_subscription = models.BooleanField("邮件订阅", default=True)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return self.username

    def get_username_display(self):
        return html.escape(self.username)

    class Meta:
        ordering = ["-score"]

    def has_coach_access(self):
        return self.rating > 1500 and self.polygon_enabled


class Payment(models.Model):

    CHANGE_USERNAME = 'change_username'
    DOWNLOAD_CASE = 'download_case'
    REWARD = 'reward'
    TRANSFER = 'transfer'
    VIEW_REPORT = 'view_report'

    TYPE_CHOICES = (
        (CHANGE_USERNAME, "更改用户名"),
        (DOWNLOAD_CASE, "下载数据"),
        (REWARD, "奖励"),
        (TRANSFER, "转账"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    detail_message = models.TextField(blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    credit = models.FloatField()  # or debit
    balance = models.FloatField()

    @property
    def detail(self):
        try:
            return json.loads(self.detail_message)
        except json.JSONDecodeError:
            return {}

    @detail.setter
    def detail(self, message):
        self.detail_message = json.dumps(message)

    class Meta:
        ordering = ["-create_time"]


class School(models.Model):
    name = models.CharField(max_length=192, unique=True)
    abbr = models.CharField(max_length=192, unique=True)
    alias = models.CharField(max_length=192, blank=True)

    def __str__(self):
        if self.alias:
            return "%s (%s)" % (self.name, self.alias)
        else: return self.name
