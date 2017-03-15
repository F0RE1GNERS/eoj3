from django.db import models
from account.models import User


class ProblemStatus(object):
    WAITING = -2
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


class Submission(models.Model):
    lang = models.CharField('Language', max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField('Code', blank=True)
    author = models.ForeignKey(User)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_start_time = models.DateTimeField(blank=True, null=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    status = models.IntegerField(default=ProblemStatus.WAITING)
    status_detail = models.TextField(blank=True)
