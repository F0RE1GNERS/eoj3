from django.db import models
from submission.models import SubmissionStatus, STATUS_CHOICE
from utils.language import LANG_CHOICE


class OldSubmission(models.Model):

    lang = models.CharField(max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField(blank=True)
    problem = models.IntegerField()
    author = models.CharField(max_length=192)

    create_time = models.DateTimeField(auto_now_add=True)
    judge_start_time = models.DateTimeField(blank=True, null=True)
    judge_end_time = models.DateTimeField(blank=True, null=True)

    status = models.IntegerField(choices=STATUS_CHOICE, default=SubmissionStatus.WAITING)
    status_percent = models.IntegerField(default=0)
    status_detail = models.TextField(blank=True)
    status_time = models.IntegerField(default=0)
    status_memory = models.IntegerField(default=0)
    code_length = models.IntegerField(default=0)

    class Meta:
        ordering = ["-pk"]

    def get_verdict_color(self):
        return ''


class OldUser(models.Model):

    username = models.CharField(max_length=192)
    password = models.CharField(max_length=192)
    school = models.CharField(max_length=192)
    email = models.CharField(max_length=192)


class OldDiscussion(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=192)
    create_time = models.DateTimeField(auto_now_add=True)
    problem = models.IntegerField()

