import shortuuid
from django.db import models
from django.utils import timezone

from account.models import User
from problem.models import Problem
from utils.language import LANG_CHOICE


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


def get_language_all_list():
    return ', '.join(sorted(dict(LANG_CHOICE).keys()))


class ContestManager(models.Manager):

    def get_status_list(self, all=False):
        if all:
            contest_list = super(ContestManager, self).get_queryset().all()
        else:
            contest_list = super(ContestManager, self).get_queryset().filter(visible=True).all()
        contest_list = contest_list.order_by("-start_time")
        for contest in contest_list:
            contest.status = contest.get_status()
            contest.participant_size = contest.participants.count()
            contest.length = contest.end_time - contest.start_time
        return contest_list


class Contest(models.Model):

    RULE_CHOICE = (
        ('acm', 'ACM Rule'),
        ('oi', 'OI Rule'),
        ('oi2', 'Traditional OI Rule'),
    )

    title = models.CharField(max_length=48)
    description = models.TextField(blank=True)
    rule = models.CharField('Rule', max_length=12, choices=RULE_CHOICE, default='acm')
    allowed_lang = models.CharField('Allowed languages', max_length=192, default=get_language_all_list())
    created_by = models.ForeignKey(User, related_name='created_contests')

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)
    freeze = models.BooleanField(default=False)
    freeze_time = models.DateTimeField(blank=True, null=True)
    standings_update_time = models.DateTimeField(blank=True, null=True)

    problems = models.ManyToManyField(Problem, through='ContestProblem')
    participants = models.ManyToManyField(User, through='ContestParticipant', related_name='contests')

    visible = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    standings_public = models.BooleanField(default=True)

    objects = ContestManager()
    contest_header = models.TextField('Header of standings', blank=True)

    class Meta:
        ordering = ['-pk']

    def get_status(self):
        now = timezone.now()
        if self.start_time <= now <= self.end_time:
            return 'running'
        elif now < self.start_time:
            return 'pending'
        else:
            return 'ended'

    def get_frozen(self):
        if self.rule == 'oi2' and self.start_time <= timezone.now() <= self.end_time:
            return 'f2' # You cannot see the result of yourself
        if self.freeze and self.freeze_time <= timezone.now() <= self.end_time:
            return 'f'  # You cannot see other participants' result
        return 'a'  # Available


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
        return self.identifier + '. ' + self.problem.title


class ContestClarification(models.Model):
    STATUS_CHOICE = (
        ('open', 'Question'),
        ('solve', 'Solved'),
        ('close', 'No Response'),
        ('note', 'Clarification')
    )

    contest = models.ForeignKey(Contest)
    text = models.TextField(blank=True)
    time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICE)
    author = models.ForeignKey(User)

    class Meta:
        ordering = ["-time"]

    def __str__(self):
        return self.text


class ContestParticipant(models.Model):
    user = models.ForeignKey(User)
    comment = models.TextField(blank=True)
    contest = models.ForeignKey(Contest)
    score = models.IntegerField(default=0)
    penalty = models.IntegerField(default=0)
    html_cache = models.TextField(blank=True)
    rank = models.IntegerField(default=0)

    class Meta:
        unique_together = ["user", "contest"]
        ordering = ["rank"]


class ContestInvitation(models.Model):
    contest = models.ForeignKey(Contest)
    code = models.CharField(max_length=24)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('contest', 'code')
        ordering = ['-pk']
