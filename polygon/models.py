from django.db import models
from account.models import User


class EditSession(models.Model):

    start_time = models.DateTimeField()
    user = models.ForeignKey(User)
    fingerprint = models.CharField(max_length=64)
    problem_repo = models.CharField(max_length=32)

