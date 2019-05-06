from django.db import models

from account.models import User


class FeedbackCompare(models.Model):
  user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
  problem_1 = models.PositiveIntegerField()
  problem_2 = models.PositiveIntegerField()
  create_time = models.DateTimeField(auto_now_add=True)
