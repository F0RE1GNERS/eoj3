from django.db import models
from django.contrib.auth.models import AbstractUser


class Privilege(object):
    REGULAR_USER = "user"
    ADMIN = "admin"
    ROOT = "root"


PRIVILEGE_CHOICE = (
    ('user', 'Regular User'),
    ('admin', 'Admin'),
    ('root', 'Root')
)


class User(AbstractUser):
    username = models.CharField('username', max_length=30, unique=True, error_messages={
        'unique': "A user with that username already exists."
    })
    email = models.EmailField('email', max_length=256, unique=True, error_messages={
        'unique': "This email has already been registered."
    })
    privilege = models.CharField(choices=PRIVILEGE_CHOICE, max_length=12, default=Privilege.REGULAR_USER)
    school = models.CharField('school', max_length=256, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
