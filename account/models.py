from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.language import LANG_CHOICE


class Privilege(object):
    REGULAR_USER = "user"
    ADMIN = "admin"
    ROOT = "root"


PRIVILEGE_CHOICE = (
    ('user', 'Regular User'),
    ('admin', 'Admin'),
    ('root', 'Root')
)


MAGIC_CHOICE = (
    ('red', 'Red'),
    ('green', 'Green'),
    ('cyan', 'Cyan'),
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
    school = models.CharField('school', max_length=192, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField('nickname', max_length=192, blank=True)
    magic = models.CharField('magic', choices=MAGIC_CHOICE, max_length=18, blank=True)
    show_tags = models.BooleanField('show tags', default=True)
    preferred_lang = models.CharField('preferred language', choices=LANG_CHOICE, max_length=12, default='cpp')

    def __str__(self):
        return self.username

    def get_username_display(self):
        if self.nickname:
            name = self.nickname
        else:
            name = self.username
        if self.magic:
            return '<span class="magic %s">%s</span>' % (self.magic, name)
        else:
            return '<span class="no-magic">%s</span>' % name
