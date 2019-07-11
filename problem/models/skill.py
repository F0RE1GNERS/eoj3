from django.db import models


class Skill(models.Model):
  name = models.CharField(max_length=64)
  description = models.TextField(blank=True)
  parent_id = models.IntegerField(default=-1)
  problem_list = models.TextField(blank=True)
  priority = models.IntegerField(default=0)

  @property
  def parsed_problem_list(self):
    return list(map(int, filter(lambda x: x, self.problem_list.split(','))))
