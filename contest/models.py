from django.db import models
from django.db import IntegrityError
from django.utils import timezone

from account.models import User
from problem.models import Problem
import shortuuid


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


class ContestManager(models.Manager):

    def get_status_list(self):
        cmp = dict(Running=-1, Pending=0, Ended=1)
        contest_list = super(ContestManager, self).get_queryset().all()
        for contest in contest_list:
            contest.status = contest.get_status()
        contest_list = sorted(contest_list, key=lambda c: cmp[c.status])
        return contest_list


class Contest(models.Model):
    RULE_CHOICE = (
        ('acm', 'ACM Rule'),
        ('oi', 'OI Rule')
    )

    title = models.CharField(max_length=48)
    description = models.TextField(blank=True)
    rule = models.CharField('Rule', max_length=12, choices=RULE_CHOICE, default='acm')
    created_by = models.ForeignKey(User, related_name='created_contests')

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)

    problems = models.ManyToManyField(Problem, through='ContestProblem')
    participants = models.ManyToManyField(User, through='ContestParticipant', related_name='contests')

    visible = models.BooleanField(default=False)
    public = models.BooleanField(default=False)

    objects = ContestManager() # ???
    contest_header = models.TextField('Header of standings', blank=True)

    class Meta:
        ordering = ['-pk']

    def get_status(self):
        now = timezone.now()
        if self.start_time <= now <= self.end_time:
            return 'Running'
        elif now <= self.start_time:
            return 'Pending'
        else:
            return 'Ended'


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem)
    contest = models.ForeignKey(Contest)
    identifier = models.CharField(max_length=12)
    total_submit_number = models.IntegerField(default=0)
    total_accept_number = models.IntegerField(default=0)

    class Meta:
        unique_together = ('problem', 'contest')
        ordering = ['identifier']

    def add_submit(self, add=1):
        # Added when submitting
        self.total_submit_number += add

    def add_accept(self, add=1):
        self.total_accept_number += add

    def __str__(self):
        return self.identifier + ' - ' + self.problem.title


class ContestClarification(models.Model):
    contest = models.ForeignKey(Contest)
    question = models.TextField()
    answer = models.TextField(blank=True)
    username = models.CharField(max_length=30)


class ContestParticipant(models.Model):
    user = models.ForeignKey(User)
    comment = models.TextField(blank=True)
    contest = models.ForeignKey(Contest)
    score = models.IntegerField(default=0)
    penalty = models.IntegerField(default=0)
    html_cache = models.TextField(blank=True)

    class Meta:
        unique_together = ["user", "contest"]
        ordering = ["-score", "penalty"]


class ContestInvitation(models.Model):

    contest = models.ForeignKey(Contest)
    code = models.CharField(max_length=24)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('contest', 'code')
        ordering = ['-pk']
