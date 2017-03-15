from django.db import models


class Server(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ip = models.CharField(max_length=30)
    port = models.IntegerField()
    token = models.CharField(max_length=256)
    add_time = models.DateTimeField(auto_now_add=True)
    last_seen_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return

    class Meta:
        ordering = ["last_seen_time"]
