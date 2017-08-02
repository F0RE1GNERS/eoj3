from django.db import models
from account.models import User
from problem.models import Problem
from contest.models import Contest
from utils.language import LANG_CHOICE, transform_code_to_html
from utils.time import datetime_display


class SubmissionStatus(object):

    SUBMITTED = -4
    WAITING = -3
    JUDGING = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    TIME_LIMIT_EXCEEDED = 1
    IDLENESS_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    RUNTIME_ERROR = 4
    SYSTEM_ERROR = 5
    COMPILE_ERROR = 6
    JUDGE_ERROR = 11
    PRETEST_PASSED = 12

    @staticmethod
    def is_judged(status):
        return status >= SubmissionStatus.WRONG_ANSWER

    @staticmethod
    def is_penalty(status):
        return SubmissionStatus.is_judged(status) and status != SubmissionStatus.COMPILE_ERROR


STATUS_CHOICE = (
    (-4, 'Submitted'),
    (-3, 'Waiting'),
    (-2, 'Judging'),
    (-1, 'Wrong Answer'),
    (0, 'Accepted'),
    (1, 'Time Limit Exceeded'),
    (2, 'Idleness Limit Exceeded'),
    (3, 'Memory Limit Exceeded'),
    (4, 'Runtime Error'),
    (5, 'System Error'),
    (6, 'Compile Error'),
    (7, 'Idleness Limit Exceeded'),
    (8, 'Time Limit Exceeded'),
    (11, 'Judge Error'),
    (12, 'Pretest Passed')
)


class Submission(models.Model):

    lang = models.CharField('Language', max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField('Code', blank=True)
    problem = models.ForeignKey(Problem)
    author = models.ForeignKey(User)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    status = models.IntegerField(choices=STATUS_CHOICE, default=SubmissionStatus.WAITING)
    status_detail = models.TextField(blank=True)
    status_time = models.FloatField(default=0)

    # if contest is null, then it is visible outside
    contest = models.ForeignKey(Contest, null=True)

    addon_info = models.BooleanField(default=False)

    class Meta:
        ordering = ['-pk']

    @property
    def verbose_status(self):
        return dict(STATUS_CHOICE)[self.status]

    @property
    def create_time_display(self):
        return datetime_display(self.create_time)

    @property
    def judge_time_display(self):
        return datetime_display(self.judge_end_time)

    @property
    def code_as_html(self):
        return transform_code_to_html(self.code, self.lang)

    def is_judged(self):
        return SubmissionStatus.is_judged(self.status)

    def get_time_display(self):
        if self.status >= SubmissionStatus.WRONG_ANSWER and self.status != SubmissionStatus.COMPILE_ERROR:
            return '%.3fs' % self.status_time

    def get_status_display_in_contest(self):
        addition = ''
        if self.contest is not None and (self.contest.rule == 'oi' or self.contest.rule == 'oi2') and self.is_judged():
            addition = ' %d%%' % self.status_percent
        return self.get_status_display() + addition
