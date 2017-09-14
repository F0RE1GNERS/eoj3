import random
import json
import html
from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.language import LANG_CHOICE
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill


class Privilege(object):
    REGULAR_USER = "user"
    ADMIN = "admin"
    ROOT = "root"
    VOLUNTEER = "volunteer"


PRIVILEGE_CHOICE = (
    ('user', 'Regular User'),
    ('admin', 'Admin'),
    ('root', 'Root'),
    ('volunteer', 'Volunteer'),
)


MAGIC_CHOICE = (
    ('red', 'Red'),
    ('green', 'Green'),
    ('teal', 'Teal'),
    ('blue', 'Blue'),
    ('purple', 'Purple'),
    ('orange', 'Orange'),
    ('grey', 'Grey'),
)


class User(AbstractUser):
    username = models.CharField('username', max_length=30, unique=True, error_messages={
        'unique': "A user with that username already exists."
    })
    email = models.EmailField('email', max_length=192, unique=True, error_messages={
        'unique': "This email has already been used."
    })
    privilege = models.CharField(choices=PRIVILEGE_CHOICE, max_length=12, default=Privilege.REGULAR_USER)
    school = models.CharField('school', max_length=64, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField('nickname', max_length=30, blank=True)
    magic = models.CharField('magic', choices=MAGIC_CHOICE, max_length=18, blank=True)
    show_tags = models.BooleanField('show tags', default=True)
    preferred_lang = models.CharField('preferred language', choices=LANG_CHOICE, max_length=12, default='cpp')
    motto = models.CharField('motto', max_length=192, blank=True)

    avatar = models.ImageField('avatar', upload_to='avatar', default='avatar/default.jpg')
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

    def __str__(self):
        return self.username

    def get_username_display(self):
        return html.escape(self.nickname or self.username)

    class Meta:
        ordering = ["-score"]


class Payment(models.Model):

    CHANGE_USERNAME = 'change_username'
    DOWNLOAD_CASE = 'download_case'
    REWARD = 'reward'
    TRANSFER = 'transfer'

    TYPE_CHOICES = (
        (CHANGE_USERNAME, 'Change Username'),
        (DOWNLOAD_CASE, 'Download Case'),
        (REWARD, 'Reward'),
        (TRANSFER, 'Transfer'),
    )

    user = models.ForeignKey(User)
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
