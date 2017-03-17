from django.db import models

from account.models import User
from problem.models import Problem
from group.models import Group


class Contest(models.Model):
    title = models.CharField(max_length=48)
    description = models.TextField()
    created_by = models.ForeignKey(User)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(Group)
    problems = models.ManyToManyField(Problem, through='ContestProblem')

    visible = models.BooleanField(default=False)


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem)
    contest = models.ForeignKey(Contest)
    identifier = models.CharField(max_length=12)
    total_submit_number = models.IntegerField(default=0)
    total_accept_number = models.IntegerField(default=0)

    class Meta:
        unique_together = ('problem', 'contest')


class ContestClarification(models.Model):
    contest = models.ForeignKey(Contest)
    question = models.TextField()
    answer = models.TextField(blank=True)
    username = models.CharField(max_length=30)
