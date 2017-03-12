from django.db import models
from django.contrib.auth.models import AbstractUser


class Privilege(object):
    REGULAR_USER = "Regular User"
    ADMIN = "Admin"
    ROOT = "Root"


class User(AbstractUser):
    username = models.CharField(max_length=30, unique=True, error_messages={
        'unique': "A user with that username already exists."
    })
    email = models.EmailField(max_length=256, unique=True, error_messages={
        'unique': "This email has already been registered."
    })
    privilege = models.CharField(max_length=24, default=Privilege.REGULAR_USER)
    school = models.CharField(max_length=256, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
