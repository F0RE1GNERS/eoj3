from django.db import models
from account.models import User


class Problem(models.Model):
    title = models.CharField(max_length=128)
    description = models.TextField()
    created_by = models.ForeignKey(User)

    visible = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)

    time_limit = models.IntegerField
    memory_limit = models.IntegerField

    total_submit_number = models.IntegerField(default=0)
    total_accepted_number = models.IntegerField(default=0)
