from django.db import models
from account.models import User


class Submission(models.Model):
    lang = models.CharField(max_length=12)
    code = models.TextField()
    author = models.ForeignKey(User)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_start_time = models.DateTimeField(blank=True, null=True)
    judge_end_time = models.DateTimeField(blank=True, null=False)

    status = models.CharField(max_length=32)
    status_detail = models.TextField()
