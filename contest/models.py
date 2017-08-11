import shortuuid
from django.db import models
from django.utils import timezone

from account.models import User
from problem.models import Problem
from utils.language import LANG_CHOICE


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


def get_language_all_list():
    return ','.join(sorted(dict(LANG_CHOICE).keys()))


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

    SCORING_METHOD_CHOICE = (
        ('acm', 'ACM Rule'),
        ('oi', 'OI Rule'),
        ('cf', 'Codeforces Rule')
    )

    TEST_DURING_CONTEST_CHOICE = (
        ('none', 'None'),
        ('sample', 'Samples'),
        ('pretest', 'Pretests'),
        ('all', 'All')
    )

    CODE_SHARE_CHOICE = (
        (0, 'Forbidden'),
        (1, 'Share code after contest for AC Users'),
        (2, 'Share code after contest for all'),
        (3, 'Share code after AC during contest'),
    )

    CONTEST_STATUS_CHOICE = (
        (1, 'Running'),
        (2, 'Ended'),
    )

    title = models.CharField(max_length=192)
    description = models.TextField(blank=True)
    allowed_lang = models.CharField('Allowed languages', max_length=192, default=get_language_all_list())

    always_running = models.BooleanField(default=False)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    standings_update_time = models.DateTimeField(blank=True, null=True)

    freeze = models.BooleanField('The standings will be frozen', default=False)
    freeze_time = models.DateTimeField(blank=True, null=True)
    scoring_method = models.CharField(default='acm', max_length=5, choices=SCORING_METHOD_CHOICE)
    run_tests_during_contest = models.CharField(max_length=10, choices=TEST_DURING_CONTEST_CHOICE, default='all')
    allow_code_share = models.IntegerField(default=1, choices=CODE_SHARE_CHOICE)  # Can view others' codes after AC

    last_counts = models.BooleanField('The last submission (instead of the best) will be scored', default=False)  # Treat last submission as valid submission
    penalty_counts = models.BooleanField('Use penalty to sort participants with the same score', default=True)  # Whether penalty counts in case of the same scores
    standings_without_problem = models.BooleanField('Show standings without a list of solved problems (often used when there is too many problems)',
                                                    default=False)  # Have a standing without specific problems
    standings_public = models.BooleanField('Make standings public even if the contest is private', default=True)
    standings_disabled = models.BooleanField("Users won't be able to see their standings in any case", default=False)

    system_tested = models.BooleanField(default=False)  # Passing system test or not, shall be available for run_tests_during_contest none, sample and pretest

    problems = models.ManyToManyField(Problem, through='ContestProblem')
    participants = models.ManyToManyField(User, through='ContestParticipant', related_name='contests')

    visible = models.BooleanField(default=False)
    public = models.BooleanField(default=False)

    objects = ContestManager()
    manager = models.ManyToManyField(User, related_name='managing_contests')

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

    @property
    def supported_language_list(self):
        return list(filter(lambda x: x, self.allowed_lang.split(',')))


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem)
    contest = models.ForeignKey(Contest)
    identifier = models.CharField(max_length=12)
    weight = models.IntegerField(default=100)

    class Meta:
        unique_together = ('problem', 'contest')
        ordering = ['identifier']

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
    answer = models.TextField(blank=True)

    class Meta:
        ordering = ["-time"]

    def __str__(self):
        return self.text


class ContestParticipant(models.Model):
    user = models.ForeignKey(User)
    star = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    hidden_comment = models.TextField(blank=True)
    contest = models.ForeignKey(Contest)
    score = models.IntegerField(default=0)
    penalty = models.IntegerField(default=0)
    html_cache = models.TextField(blank=True)
    rank = models.IntegerField(blank=True, null=True)

    class Meta:
        unique_together = ["user", "contest"]
        ordering = ["-score", "penalty"]


class ContestInvitation(models.Model):
    contest = models.ForeignKey(Contest)
    star = models.BooleanField(default=False)
    code = models.CharField(max_length=24)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('contest', 'code')
        ordering = ['-pk']
