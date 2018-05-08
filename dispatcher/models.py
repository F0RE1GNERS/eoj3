from django.db import models
from problem.models import Problem


class Server(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ip = models.CharField(max_length=30)
    port = models.IntegerField()
    token = models.CharField(max_length=192)
    add_time = models.DateTimeField(auto_now_add=True)
    last_seen_time = models.DateTimeField(auto_now=True)
    last_synchronize_time = models.DateTimeField(null=True)
    enabled = models.BooleanField(default=False)
    concurrency = models.PositiveIntegerField(default=1)
    runtime_multiplier = models.FloatField(default=1)

    def __str__(self):
        return self.name + ' - ' + self.ip

    class Meta:
        ordering = ["last_seen_time"]

    @property
    def http_address(self):
        return 'http://' + self.ip + ':' + str(self.port)
