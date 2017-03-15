from django.db import models
from account.models import User


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


class Submission(models.Model):
    lang = models.CharField(max_length=12)
    code = models.TextField(blank=True)
    author = models.ForeignKey(User)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_start_time = models.DateTimeField(blank=True, null=True)
    judge_end_time = models.DateTimeField(blank=True, null=False)

    status = models.IntegerField(default=WAITING)
    status_detail = models.TextField(blank=True)
