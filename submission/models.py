from django.db import models
from account.models import User
from problem.models import Problem


class SubmissionStatus(object):
    WAITING = -3
    JUDGING = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    CPU_TIME_LIMIT_EXCEEDED = 1
    REAL_TIME_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    RUNTIME_ERROR = 4
    SYSTEM_ERROR = 5
    COMPILE_ERROR = 6
    IDLENESS_LIMIT_EXCEEDED = 7
    SUM_TIME_LIMIT_EXCEEDED = 8


LANG_CHOICE = (
    ('c', 'C'),
    ('cpp', 'C++'),
    ('python', 'Python'),
    ('java', 'Java')
)


def get_color_from_status(status):
    if status == SubmissionStatus.ACCEPTED:
        return "success"
    elif status <= SubmissionStatus.JUDGING:
        return "info"
    elif status == SubmissionStatus.COMPILE_ERROR or status == SubmissionStatus.IDLENESS_LIMIT_EXCEEDED:
        return "warning"
    elif status == SubmissionStatus.RUNTIME_ERROR or status == SubmissionStatus.SYSTEM_ERROR:
        return "warning"
    else:
        return "danger"


class Submission(models.Model):

    STATUS_CHOICE = (
        (-3, 'Waiting'),
        (-2, 'Judging'),
        (-1, 'Wrong Answer'),
        (0, 'Accepted'),
        (1, 'Time Limit Exceeded'),
        (2, 'Time Limit Exceeded'),
        (3, 'Memory Limit Exceeded'),
        (4, 'Runtime Error'),
        (5, 'System Error'),
        (6, 'Compile Error'),
        (7, 'Idleness Limit Exceeded'),
        (8, 'Time Limit Exceeded')
    )

    lang = models.CharField('Language', max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField('Code', blank=True)
    problem = models.ForeignKey(Problem)
    author = models.ForeignKey(User)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_start_time = models.DateTimeField(blank=True, null=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    # TODO: add choices?
    status = models.IntegerField(choices=STATUS_CHOICE, default=SubmissionStatus.WAITING)
    status_detail = models.TextField(blank=True)
    status_time = models.IntegerField(default=0)
    status_memory = models.IntegerField(default=0)
    code_length = models.IntegerField(default=0)

    def is_judged(self):
        return self.status >= SubmissionStatus.WRONG_ANSWER

    def get_verdict_color(self):
        return get_color_from_status(self.status)

    def get_time_display(self):
        if self.status >= SubmissionStatus.WRONG_ANSWER and self.status != SubmissionStatus.COMPILE_ERROR:
            return str(self.status_time) + "ms"
        else:
            return "N/A"

    def get_memory_display(self):
        if self.status >= SubmissionStatus.WRONG_ANSWER and self.status != SubmissionStatus.COMPILE_ERROR:
            return str(self.status_memory) + "B"
        else:
            return "N/A"