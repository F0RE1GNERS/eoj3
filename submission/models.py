from django.db import models
from account.models import User
from problem.models import Problem
from contest.models import Contest
from utils.language import LANG_CHOICE, transform_code_to_html
from utils.time import datetime_display
import json


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

    @staticmethod
    def is_accepted(status):
        return status == SubmissionStatus.ACCEPTED or status == SubmissionStatus.PRETEST_PASSED


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

    create_time = models.DateTimeField(auto_now_add=True, db_index=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    status = models.IntegerField(choices=STATUS_CHOICE, db_index=True, default=SubmissionStatus.SUBMITTED)
    status_private = models.IntegerField(choices=STATUS_CHOICE, default=SubmissionStatus.SUBMITTED)
    status_percent = models.FloatField(default=0)
    # Private Status has to be accurate, because you yourself know more than others
    # add empty dict to detail list if there are still cases to judge
    status_detail = models.TextField(blank=True)
    status_time = models.FloatField(default=0)
    status_message = models.TextField(blank=True)
    rewarded = models.BooleanField(default=False)
    code_length = models.PositiveIntegerField(default=0)

    # if contest is null, then it is visible outside
    contest = models.ForeignKey(Contest, null=True)

    addon_info = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.code_length = len(self.code.encode())
        return super(Submission, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-create_time']

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

    @property
    def status_detail_list(self):
        try:
            return json.loads(self.status_detail)
        except json.JSONDecodeError:
            return []

    @status_detail_list.setter
    def status_detail_list(self, lis):
        self.status_detail = json.dumps(lis)

    @property
    def status_detail_display(self):
        r, l = [], self.status_detail_list
        status_dictionary = dict(STATUS_CHOICE)
        count = len(l)
        for index, s in enumerate(l, start=1):
            u, v = -233, '%d/%d' % (index, count)  # Magic number: display nothing
            if ('verdict' in s) and SubmissionStatus.is_judged(s['verdict']):
                u = s['verdict']
                t = status_dictionary[u]
                if s['verdict'] == SubmissionStatus.ACCEPTED:
                    t += ', %.3fs' % s.get('time', 0.0)
                elif s['verdict'] == SubmissionStatus.RUNTIME_ERROR:
                    t += ', %s' % s.get('message', 'NaN')
                v += ': ' + t
            r.append((u, v))
        return r

    def is_judged(self):
        return SubmissionStatus.is_judged(self.status)

    def get_time_display(self):
        if self.status >= SubmissionStatus.WRONG_ANSWER and self.status != SubmissionStatus.COMPILE_ERROR:
            return '%.3f' % self.status_time
        else:
            return 'NaN'

    def get_status_display_in_contest(self):
        addition = ''
        if self.contest is not None and (self.contest.rule == 'oi' or self.contest.rule == 'oi2') and self.is_judged():
            addition = ' %d%%' % self.status_percent
        return self.get_status_display() + addition

    @property
    def partial_score(self):
        if not hasattr(self, '_partial_score'):
            self._partial_score = sum(
                map(lambda x: x.get('score', 10) if x.get('verdict', -1) == 0 else 0, self.status_detail_list))
        return self._partial_score
