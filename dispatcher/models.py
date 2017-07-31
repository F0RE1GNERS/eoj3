from django.db import models
from problem.models import Problem


DEFAULT_USERNAME = 'ejudge'


class Server(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ip = models.CharField(max_length=30)
    port = models.IntegerField()
    token = models.CharField(max_length=192)
    add_time = models.DateTimeField(auto_now_add=True)
    last_seen_time = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name + ' - ' + self.ip

    class Meta:
        ordering = ["last_seen_time"]
