import json
import html

from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import BaseValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.language import LANG_CHOICE
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.utils.translation import ugettext_lazy as _


MAGIC_CHOICE = (
    ('red', 'Red'),
    ('green', 'Green'),
    ('teal', 'Teal'),
    ('blue', 'Blue'),
    ('purple', 'Purple'),
    ('orange', 'Orange'),
    ('grey', 'Grey'),
)


class UsernameValidator(UnicodeUsernameValidator):
    regex = r'^[\w.+-]+$'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and ./+/-/_ characters.'
    )


class UsernameLengthValidator(BaseValidator):
    message = _("Username should contain at least 6 characters.")
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

    username = models.CharField(_('username'), max_length=30, unique=True,
                                validators=username_validators,
                                error_messages={
                                    'unique': _("A user with that username already exists.")}
                                )
    email = models.EmailField(_('email'), max_length=192, unique=True, error_messages={
        'unique': _("This email has already been used.")
    })
    school = models.CharField(_('school'), max_length=64, blank=True)
    name = models.CharField(_('name'), max_length=30, blank=True)
    student_id = models.CharField(_('student id'), max_length=30, blank=True)
    magic = models.CharField(_('magic'), choices=MAGIC_CHOICE, max_length=18, blank=True)
    show_tags = models.BooleanField(_('show tags'), default=True)
    preferred_lang = models.CharField(_('preferred language'), choices=LANG_CHOICE, max_length=12, default='cpp')
    motto = models.CharField(_('motto'), max_length=192, blank=True)

    avatar = models.ImageField(_('avatar'), upload_to='avatar', default='avatar/default.jpg')
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
    email_subscription = models.BooleanField(default=True)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return self.username

    def get_username_display(self):
        return html.escape(self.username)

    class Meta:
        ordering = ["-score"]


class Payment(models.Model):

    CHANGE_USERNAME = 'change_username'
    DOWNLOAD_CASE = 'download_case'
    REWARD = 'reward'
    TRANSFER = 'transfer'
    VIEW_REPORT = 'view_report'

    TYPE_CHOICES = (
        (CHANGE_USERNAME, _('Change Username')),
        (DOWNLOAD_CASE, _('Download Case')),
        (REWARD, _('Reward')),
        (TRANSFER, _('Transfer')),
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

    class Meta:
        ordering = ["-create_time"]


class School(models.Model):
    name = models.CharField(max_length=192, unique=True)

    def __str__(self):
        return self.name
