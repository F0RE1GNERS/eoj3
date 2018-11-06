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
    SCORED = 7
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

    @staticmethod
    def is_scored(status):
        return status == SubmissionStatus.SCORED


STATUS_CHOICE = (
    (-4, 'Submitted'),
    (-3, 'In queue'),
    (-2, 'Running'),
    (-1, 'Wrong answer'),
    (0, 'Accepted'),
    (1, 'Time limit exceeded'),
    (2, 'Idleness limit exceeded'),
    (3, 'Memory limit exceeded'),
    (4, 'Runtime error'),
    (5, 'Denial of judgement'),
    (6, 'Compilation error'),
    (7, 'Partial score'),
    (11, 'Checker error'),
    (12, 'Pretest passed'),
)


class Submission(models.Model):

    lang = models.CharField(max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField(blank=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    create_time = models.DateTimeField(auto_now_add=True, db_index=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    status = models.IntegerField(choices=STATUS_CHOICE, db_index=True, default=SubmissionStatus.SUBMITTED)
    status_percent = models.FloatField(default=0)
    # Private Status has to be accurate, because you yourself know more than others
    # add empty dict to detail list if there are still cases to judge
    status_detail = models.TextField(blank=True)
    status_time = models.FloatField(default=0)
    status_message = models.TextField(blank=True)
    status_test = models.PositiveIntegerField(default=0)
    code_length = models.PositiveIntegerField(default=0)
    judge_server = models.IntegerField(default=0)

    # if contest is null, then it is visible outside
    contest = models.ForeignKey(Contest, on_delete=models.SET_NULL, null=True)

    addon_info = models.BooleanField(default=False)   # balloon
    ip = models.GenericIPAddressField(blank=True, null=True)
    cheat_tag = models.IntegerField(default=0)
    report_paid = models.IntegerField(default=0)

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
        re_count, last_group = 1, 0
        for index, s in enumerate(l, start=1):
            u, v = -233, '%d/%d' % (index, count)  # Magic number: display nothing
            if 'verdict' in s:
                if 'group' in s:
                    if s['group'] != last_group:
                        re_count = 1
                    last_group = s['group']
                    u = s['verdict']
                    v = '%d-%d' % (s['group'], re_count)
                    re_count += 1
                if SubmissionStatus.is_judged(s['verdict']):
                    u = s['verdict']
                    t = status_dictionary[u]
                    if s['verdict'] in (SubmissionStatus.ACCEPTED, SubmissionStatus.SCORED, ):
                        t += ', %.3fs' % s.get('time', 0.0)
                    elif s['verdict'] == SubmissionStatus.RUNTIME_ERROR:
                        t += ', %s' % s.get('message', 'NaN')
                    v += ': ' + t
                elif 'group' in s:
                    v += ": Skipped"
            if 'point' in s:
                v += ' (%.1f)' % s['point']
            r.append((u, v))
        return r

    @property
    def is_judged(self):
        return SubmissionStatus.is_judged(self.status)

    def get_time_display(self):
        if self.status >= SubmissionStatus.WRONG_ANSWER and self.status != SubmissionStatus.COMPILE_ERROR:
            return '%.3f' % self.status_time
        else:
            return 'NaN'

    @property
    def status_score(self):
        if hasattr(self, 'contest_problem'):
            return int(round(self.contest_problem.weight / 100 * self.status_percent + 1E-2))
        return int(round(self.status_percent))


class PrintManager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limit = models.PositiveIntegerField(default=50)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)


class PrintCode(models.Model):
    code = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    manager = models.ForeignKey(PrintManager, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    generated_pdf = models.TextField(blank=True)
    pages = models.PositiveIntegerField(default=1)
    status = models.IntegerField(choices=(
        (-1, 'Processing'), (0, 'OK'), (1, 'Failed'), (2, 'Ignore')
    ), default=-1)
    comment = models.CharField(blank=True, max_length=64)
