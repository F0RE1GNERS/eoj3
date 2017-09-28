from django.db import models
from django.db.models import Sum, Case, When, IntegerField
from account.models import User
from problem.models import Problem


class BlogQuerySet(models.QuerySet):
    def with_likes(self):
        return self.annotate(
                likes__count=Sum(Case(When(bloglikes__flag='like', then=1), default=0, output_field=IntegerField()))
        )

    def with_dislikes(self):
        return self.annotate(
                dislikes__count=Sum(Case(When(bloglikes__flag='dislike', then=1), default=0, output_field=IntegerField()))
        )

    def with_likes_flag(self, user):
        return self.annotate(
                likes__flag=Sum(
                    Case(When(bloglikes__user=user, bloglikes__flag='like', then=1),
                         When(bloglikes__user=user, bloglikes__flag='dislike', then=-1), default=0, output_field=IntegerField()))
        )


class Blog(models.Model):
    title = models.CharField('Title', max_length=128)
    text = models.TextField('Text')
    author = models.ForeignKey(User)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    edit_time = models.DateTimeField('Edit time', auto_now=True)

    likes = models.ManyToManyField(User, through='BlogLikes', related_name='blog_user_like')

    objects = BlogQuerySet.as_manager()

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

    class Meta:
        unique_together = ('blog', 'user')


class Comment(models.Model):
    text = models.TextField('Text')
    author = models.ForeignKey(User)
    create_time = models.DateTimeField('Created time', auto_now_add=True)
    blog = models.ForeignKey(Blog, null=True)
    problem = models.ForeignKey(Problem, null=True)

    class Meta:
        ordering = ["-create_time"]
