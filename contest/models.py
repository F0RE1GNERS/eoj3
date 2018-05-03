import shortuuid
from django.core.validators import EmailValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from account.models import User, School
from problem.models import Problem
from utils.language import LANG_CHOICE


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


def get_language_all_list():
    return ','.join(sorted(dict(LANG_CHOICE).keys()))


class ContestManager(models.Manager):

    def get_status_list(self, show_all=False, filter_user=None, sorting_by_id=False, always_running=None):
        q = models.Q()
        if not show_all:
            q &= models.Q(visible=True)
            if filter_user:
                q |= models.Q(managers=filter_user)
        if always_running is not None:
            q &= models.Q(always_running=always_running)
        contest_list = self.get_queryset().prefetch_related('authors').\
            annotate(Count('participants', distinct=True)).filter(q)

        if sorting_by_id:
            contest_list = contest_list.order_by("-pk").distinct()
        else:
            contest_list = contest_list.order_by("-start_time").distinct()
            for contest in contest_list:
                contest.length = contest.end_time - contest.start_time
        return contest_list


class Contest(models.Model):

    SCORING_METHOD_CHOICE = (
        ('acm', _('ACM Rule')),
        ('oi', _('OI Rule')),
        ('cf', _('School of Data Analysis (SDA) Rule')),
        ('tcmtime', "TCM/TIME Rule")
    )

    TEST_DURING_CONTEST_CHOICE = (
        ('all', _('All')),
        ('pretest', _('Pretests')),
        ('sample', _('Samples')),
        ('none', _('None'))
    )

    CODE_SHARE_CHOICE = (
        (0, _('Forbidden')),
        (1, _('Share code after contest for AC users')),
        (2, _('Share code after contest for all')),
        (3, _('Share code after AC during contest')),
    )

    CONTEST_STATUS_CHOICE = (
        (1, _('Running')),
        (2, _('Ended')),
    )

    title = models.CharField(max_length=192)
    description = models.TextField(blank=True)
    allowed_lang = models.CharField(_('Allowed languages'), max_length=192, default=get_language_all_list())

    always_running = models.BooleanField(default=False)
    start_time = models.DateTimeField(blank=True, null=True, default=timezone.now)
    end_time = models.DateTimeField(blank=True, null=True, default=timezone.now)
    create_time = models.DateTimeField(auto_now_add=True)
    standings_update_time = models.DateTimeField(blank=True, null=True)

    freeze = models.BooleanField(_('The standings will be frozen'), default=False)
    freeze_time = models.DateTimeField(blank=True, null=True)
    scoring_method = models.CharField(default='acm', max_length=10, choices=SCORING_METHOD_CHOICE)
    run_tests_during_contest = models.CharField(max_length=10, choices=TEST_DURING_CONTEST_CHOICE, default=TEST_DURING_CONTEST_CHOICE[0][0])
    allow_code_share = models.IntegerField(default=1, choices=CODE_SHARE_CHOICE)  # Can view others' codes after AC

    last_counts = models.BooleanField('The last submission (instead of the best) will be scored', default=False)  # Treat last submission as valid submission
    penalty_counts = models.BooleanField('Use penalty to sort participants with the same score', default=True)  # Whether penalty counts in case of the same scores
    standings_without_problem = models.BooleanField('Show standings without a list of solved problems (often used when there is too many problems)',
                                                    default=False)  # Have a standing without specific problems
    standings_public = models.BooleanField('Make standings public even if the contest is private', default=True)
    standings_disabled = models.BooleanField("Users won't be able to see their standings in any case", default=False)
    case_public = models.BooleanField('Cases can be downloaded if paid', default=False)

    system_tested = models.BooleanField(default=False)  # Passing system test or not, shall be available for run_tests_during_contest none, sample and pretest
    rated = models.BooleanField(default=False)

    problems = models.ManyToManyField(Problem, through='ContestProblem')
    participants = models.ManyToManyField(User, through='ContestParticipant', related_name='contests')

    visible = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    open_problems = models.BooleanField('Publish problems after contest', default=True)
    ip_sensitive = models.BooleanField('Bind IP to user\'s account after first login', default=False)
    analysis_blog_id = models.IntegerField(default=0)   # related to a blog id

    objects = ContestManager()
    managers = models.ManyToManyField(User, related_name='managing_contests')
    authors = models.ManyToManyField(User, related_name='written_contests')

    class Meta:
        ordering = ['-pk']

    @property
    def status(self):
        now = timezone.now()
        try:
            if self.always_running or self.start_time <= now <= self.end_time:
                return 0  # running
            elif now < self.start_time:
                return -1  # pending
            else:
                return 1  # ended
        except:
            return -2  # error

    @property
    def is_frozen(self):
        if self.freeze and self.freeze_time <= timezone.now() <= self.end_time:
            return True
        return False

    @property
    def pending_system_tests(self):
        return self.status > 0 and self.run_tests_during_contest != 'all' and not self.system_tested

    @property
    def supported_language_list(self):
        return list(filter(lambda x: x, map(lambda x: x.strip(), self.allowed_lang.split(','))))

    @property
    def verbose_supported_language_list(self):
        def rreplace(s, old, new, count):
            return (s[::-1].replace(old[::-1], new[::-1], count))[::-1]

        lang_choices = dict(LANG_CHOICE)
        return rreplace(', '.join(list(map(lambda x: lang_choices[x], self.supported_language_list))), ', ', ' and ', 1)

    @property
    def contest_problem_list(self):
        if not hasattr(self, '_contest_problem_list'):
            self._contest_problem_list = list(self.contestproblem_set.select_related('problem').
                                              defer('problem__description', 'problem__input', 'problem__output',
                                                    'problem__hint').all())
        return self._contest_problem_list

    def get_contest_problem(self, problem_id):
        get_result = list(filter(lambda p: p.problem_id == problem_id, self.contest_problem_list))
        if len(get_result) > 0:
            return get_result[0]
        else:
            return None

    def add_contest_problem_to_submissions(self, submissions):
        find_contest_problem = {k.problem_id: k for k in self.contest_problem_list}
        for submission in submissions:
            submission.contest_problem = find_contest_problem.get(submission.problem_id)

    @property
    def participants_ids(self):
        if not hasattr(self, '_contest_user_ids'):
            self._contest_user_ids = list(self.contestparticipant_set.order_by().values_list("user_id", flat=True))
        return self._contest_user_ids

    def __str__(self):
        return self.title


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

    contest = models.ForeignKey(Contest)
    text = models.TextField(blank=True)
    time = models.DateTimeField(auto_now=True)
    important = models.BooleanField(default=False)
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
    is_disabled = models.BooleanField(default=False)
    rank = models.IntegerField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        unique_together = ["user", "contest"]


class ContestInvitation(models.Model):

    contest = models.ForeignKey(Contest)
    star = models.BooleanField(default=False)
    code = models.CharField(max_length=24)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('contest', 'code')
        ordering = ['-pk']


class ContestUserRating(models.Model):
    rating = models.IntegerField(default=1500)
    user = models.ForeignKey(User)
    contest = models.ForeignKey(Contest)
    solved = models.IntegerField()
    rank = models.IntegerField()
    modified = models.DateTimeField()

    class Meta:
        unique_together = ('contest', 'user')
        ordering = ["-modified"]

    def __str__(self):
        return 'ContestUserRating: {user: %d, rating: %d}' % (self.user_id, self.rating)


class Activity(models.Model):
    title = models.CharField(unique=True, max_length=192)
    description = models.TextField(blank=True)
    author = models.ForeignKey(User)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now_add=True)
    register_start_time = models.DateTimeField(blank=True)
    register_end_time = models.DateTimeField(blank=True)
    participants = models.ManyToManyField(User, through='ActivityParticipant', related_name="activities")


class ActivityParticipant(models.Model):
    MAJOR_CHOICES = (
        ('art', 'Art'),
        ('accounting', 'Accounting'),
        ('business', 'Business'),
        ('business_admin', 'Business Administration'),
        ('chemistry', 'Chemistry'),
        ('commerce', 'Commerce'),
        ('communication', 'Communications'),
        ('ce', 'Computer Engineering'),
        ('cs', 'Computer Science'),
        ('economics', 'Economics'),
        ('education', 'Education'),
        ('ee', 'Electrical Engineering'),
        ('finance', 'Finance'),
        ('geometry', 'Geometry'),
        ('interaction', 'Human Computer Interaction'),
        ('it', 'Information Technology'),
        ('life', 'Life Science'),
        ('mechanics', 'Mechanics'),
        ('linguistics', 'Linguistics'),
        ('literature', 'Literature'),
        ('math', 'Mathematics'),
        ('se', 'Software Engineering'),
        ('philosophy', 'Philosophy'),
        ('physics', 'Physics'),
        ('politics', 'Political Science'),
        ('psycho', 'Psychology'),
        ('social', 'Social Science'),
        ('translation', 'Translation'),
        ('others', 'Others')
    )

    user = models.ForeignKey(User)
    activity = models.ForeignKey(Activity)
    real_name = models.CharField(max_length=30)
    student_id = models.CharField(max_length=30)
    school = models.ForeignKey(School)
    email = models.CharField(max_length=192, validators=[EmailValidator()])
    phone = models.CharField(max_length=30, blank=True)
    major = models.CharField(max_length=30, choices=MAJOR_CHOICES, blank=True)
    gender = models.CharField(max_length=5, choices=(
        ('m', 'Male'),
        ('f', 'Female'),
        ('d', 'Declined to answer')
    ), blank=True)
    graduate_year = models.IntegerField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'activity')
