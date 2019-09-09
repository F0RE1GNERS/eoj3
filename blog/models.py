from django.db import models
from django.db.models import Sum, Case, When, IntegerField
from account.models import User
from problem.models import Problem
from django.utils.translation import ugettext_lazy as _
from submission.models import Submission
from contest.models import Contest
from contest.models import ContestProblem


class BlogManager(models.Manager):

    def get_status_list(self, show_all=False, filter_user=None):
        q = models.Q()
        if not show_all:
            q &= models.Q(is_reward=True, contest=None)
            if (filter_user):
                q |= models.Q(contest__participants__username__contains=filter_user.username)
                q |= models.Q(contest__managers__username__contains=filter_user.username)
                q |= models.Q(contest__volunteers__username__contains=filter_user.username)
                q |= models.Q(contest__authors__username__contains=filter_user.username)
        else:
            q &= models.Q(is_reward=True)
        return self.filter(q).distinct()


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
        if not user.is_authenticated:
            return self
        return self.annotate(
            likes__flag=Sum(
                Case(When(bloglikes__user=user, bloglikes__flag='like', then=1),
                     When(bloglikes__user=user, bloglikes__flag='dislike', then=-1), default=0,
                     output_field=IntegerField()))
        )

    def get_rewards_list(self, show_all=False, filter_user=None, contest=None, flag=False):
        q = models.Q(is_reward=True)
        if not show_all:
            if flag:
                q &= models.Q(contest=contest)
            if (filter_user):
                q &= models.Q(contest=None) | models.Q(contest__participants__username__contains=filter_user.username) | models.Q(
                    contest__managers__username__contains=filter_user.username) | models.Q(
                    contest__volunteers__username__contains=filter_user.username) | models.Q(
                    contest__authors__username__contains=filter_user.username)
            else:
                q &= models.Q(contest=None)
        print(q)
        return self.filter(q).distinct()


class BlogRevision(models.Model):
    title = models.CharField(max_length=128)
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-create_time"]


class Blog(models.Model):
    title = models.CharField("标题", max_length=128)
    text = models.TextField("内容")
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    visible = models.BooleanField("对所有用户可见", default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    edit_time = models.DateTimeField(auto_now=True)

    likes = models.ManyToManyField(User, through='BlogLikes', related_name='blog_user_like')
    recommend = models.BooleanField(default=False)
    revisions = models.ManyToManyField(BlogRevision)
    hide_revisions = models.BooleanField("历史版本仅自己可见", default=False)

    objects = BlogQuerySet.as_manager()

    is_reward = models.BooleanField("是否是悬赏", default=False)
    contest = models.ForeignKey(Contest, models.SET_NULL, default=None, null=True)
    problem = models.ForeignKey(Problem, models.SET_NULL, default=None, null=True)
    submission = models.ForeignKey(Submission, models.SET_NULL, default=None, null=True)

    class Meta:
        ordering = ["-edit_time"]


class BlogLikes(models.Model):
    BLOG_LIKE_FLAGS = (
        ('like', '点赞'),
        ('dislike', '点踩')
    )

    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flag = models.CharField(max_length=8, choices=BLOG_LIKE_FLAGS)

    class Meta:
        unique_together = ('blog', 'user')


class Comment(models.Model):
    # DEPRECATED
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateTimeField(_('Created time'), auto_now_add=True)
    blog = models.ForeignKey(Blog, on_delete=models.SET_NULL, null=True)
    problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-create_time"]
