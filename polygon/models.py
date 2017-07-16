from django.db import models
from account.models import User


class EditSession(models.Model):

    create_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    fingerprint = models.CharField(max_length=64)
    problem_repo = models.CharField(max_length=32)
    last_synchronize = models.DateTimeField(blank=True)
