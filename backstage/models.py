from django.db import models


class Email(models.Model):
    title = models.CharField(max_length=192)
    content = models.TextField(blank=True)
