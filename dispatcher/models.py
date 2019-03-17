from django.db import models
from problem.models import Problem


class Server(models.Model):
  name = models.CharField("名字", max_length=30, unique=True)
  ip = models.CharField("IP", max_length=30)
  port = models.IntegerField("端口号")
  token = models.CharField("密钥", max_length=192)
  add_time = models.DateTimeField("创建时间", auto_now_add=True)
  last_seen_time = models.DateTimeField(auto_now=True)
  last_synchronize_time = models.DateTimeField(null=True)
  enabled = models.BooleanField(default=False)
  concurrency = models.PositiveIntegerField("并发量", default=1)
  runtime_multiplier = models.FloatField("运行时间调整系数", default=1)
  version = models.PositiveIntegerField("判题机版本")

  def __str__(self):
    return self.name + ' - ' + self.ip

  class Meta:
    ordering = ["last_seen_time"]

  @property
  def http_address(self):
    return 'http://' + self.ip + ':' + str(self.port)


class ServerProblemStatus(models.Model):
  server = models.ForeignKey(Server, on_delete=models.CASCADE)
  problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
  last_status = models.TextField(blank=True)
  last_synchronize = models.DateTimeField(auto_now=True)

  class Meta:
    unique_together = ('server', 'problem')
