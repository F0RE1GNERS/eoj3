from django.db import models

from tagging.models import Tag


class TagInfo(models.Model):
  tag = models.OneToOneField(Tag, on_delete=models.CASCADE)
  description = models.TextField(blank=True)
  parent_id = models.IntegerField(default=-1)
