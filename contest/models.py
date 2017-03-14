from django.db import models
from account.models import User
from problem.models import Problem


class Contest(models.Model):
    title = models.CharField(max_length=48)
    description = models.TextField()
    created_by = models.ForeignKey(User)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)

    visible = models.BooleanField(default=True)
    # allower_user


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem)
    contest = models.ForeignKey(Contest)
    total_submit_number = models.IntegerField(default=0)
    total_accept_number = models.IntegerField(default=0)


class ContestClarification(models.Model):
    contest = models.ForeignKey(Contest)
    question = models.TextField()
    answer = models.TextField()
    username = models.CharField(max_length=30)