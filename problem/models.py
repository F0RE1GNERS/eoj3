from django.db import models


class Problem(models.Model):

    title = models.CharField('Title', max_length=100, blank=True)
    description = models.TextField('Description', blank=True)
    time_limit = models.IntegerField('Time limit per test', default=1000)
    sum_time_limit = models.IntegerField('Time limit all tests', default=10000)
    memory_limit = models.IntegerField('Memory limit', default=256)
    total_submissions = models.IntegerField('Total submissions', default=0)
    accepted = models.IntegerField('Accepted', default=0)
