from django.db import models
from account.models import User
from problem.models import Problem


class Blog(models.Model):
    title = models.CharField('Title', max_length=128, blank=True)
    text = models.TextField('Text', blank=True)
    author = models.ForeignKey(User)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    edit_time = models.DateTimeField('Edit time', auto_now=True)

    class Meta:
        ordering = ["-edit_time"]


class Comment(models.Model):
    text = models.TextField('Text', blank=True)
    author = models.ForeignKey(User)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    blog = models.ForeignKey(Blog, null=True)
    problem = models.ForeignKey(Problem, null=True)

    class Meta:
        ordering = ["-create_time"]
