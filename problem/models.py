from django.db import models
from account.models import User
from utils import markdown3
from tagging.registry import register
from django.core.cache import cache
from utils.language import LANG_CHOICE
from utils import random_string


class Problem(models.Model):
    alias = models.CharField(max_length=64, unique=True, default=random_string)
    title = models.CharField(max_length=192, blank=True)
    description = models.TextField(blank=True)
    input = models.TextField(blank=True)
    output = models.TextField(blank=True)
    sample = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    source = models.CharField(max_length=128, blank=True)
    difficulty = models.FloatField(default=5.0)

    visible = models.BooleanField(default=False)
    create_time = models.DateTimeField(auto_now_add=True)

    time_limit = models.IntegerField(default=1000)
    memory_limit = models.IntegerField(default=256)
    checker = models.CharField(max_length=64, default='fcmp')
    interactor = models.CharField(blank=True, max_length=64)
    validator = models.CharField(blank=True, max_length=64)
    cases = models.TextField(blank=True)

    manager = models.ManyToManyField(User, through='ProblemManagement')

    def __str__(self):
        return '%d - %s' % (self.pk, self.title)

    class Meta:
        ordering = ["-pk"]


register(Problem)


class ProblemManagement(models.Model):
    PERMISSION_CHOICES = (
        ('a', 'ADMIN'),
        ('r', 'READ'),
        ('w', 'WRITE'),
        ('n', 'NONE'),
    )

    problem = models.ForeignKey(Problem)
    user = models.ForeignKey(User)
    permission = models.CharField(max_length=2, choices=PERMISSION_CHOICES)


class TrustedSubmission(models.Model):

    CATEGORIES = ((x, x) for x in ('checker', 'generator', 'interactor', 'validator'))

    name = models.CharField(max_length=64, primary_key=True)
    category = models.CharField(max_length=12, choices=CATEGORIES)
    lang = models.CharField('language', max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField(blank=True)


class Case(models.Model):

    name = models.CharField(max_length=64, primary_key=True)
    worth = models.CharField(max_length=254)
