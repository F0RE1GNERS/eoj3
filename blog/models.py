from django.db import models
from account.models import User
from problem.models import Problem


class Blog(models.Model):
    title = models.CharField('Title', max_length=128)
    text = models.TextField('Text')
    author = models.ForeignKey(User)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    edit_time = models.DateTimeField('Edit time', auto_now=True)

    likes = models.ManyToManyField(User, through='BlogLikes', related_name='blog_user_like')

    class Meta:
        ordering = ["-edit_time"]


class BlogLikes(models.Model):

    BLOG_LIKE_FLAGS = (
        ('like', 'Like Blog'),
        ('dislike', 'Dislike Blog')
    )

    blog = models.ForeignKey(Blog)
    user = models.ForeignKey(User)
    flag = models.CharField("Flag", max_length=8, choices=BLOG_LIKE_FLAGS)


class Comment(models.Model):
    text = models.TextField('Text')
    author = models.ForeignKey(User)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    blog = models.ForeignKey(Blog, null=True)
    problem = models.ForeignKey(Problem, null=True)

    class Meta:
        ordering = ["-create_time"]
