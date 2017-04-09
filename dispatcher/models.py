from django.db import models
from problem.models import Problem


class Server(models.Model):
    name = models.CharField(max_length=30, unique=True)
    ip = models.CharField(max_length=30)
    port = models.IntegerField()
    token = models.CharField(max_length=192)
    add_time = models.DateTimeField(auto_now_add=True)
    last_seen_time = models.DateTimeField(auto_now=True)
    problems = models.ManyToManyField(Problem, through='ServerProblemStatus')

    def __str__(self):
        return self.name + ' - ' + self.ip

    class Meta:
        ordering = ["last_seen_time"]


class ServerProblemStatus(models.Model):
    server = models.ForeignKey(Server)
    problem = models.ForeignKey(Problem)
    testdata_hash = models.CharField('Testdata hash', max_length=64, blank=True)

    def __str__(self):
        return "%s - %d" % (self.server.name, self.problem_id)
