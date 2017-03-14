from django.db import models
from account.models import User


class Group(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField()
    members = models.ManyToManyField(User)

    created_by = models.ForeignKey(User, related_name='my_groups')
