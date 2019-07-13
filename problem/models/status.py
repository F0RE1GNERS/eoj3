import django_comments
from django.db import models

from account.models import User


class UserStatus(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submission_status")
  contest_id = models.PositiveIntegerField(db_index=True)
  total_count = models.PositiveIntegerField()
  total_list = models.TextField(blank=True)
  ac_count = models.PositiveIntegerField()
  ac_distinct_count = models.PositiveIntegerField()
  ac_list = models.TextField(blank=True)
  predict_list = models.TextField(blank=True)
  update_time = models.DateTimeField(auto_now=True)

  class Meta:
    unique_together = ('user', 'contest_id')
