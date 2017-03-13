from django.db import models
from account.models import User


class Problem(models.Model):
    title = models.CharField('Title', max_length=128, blank=True)
    description = models.TextField('Description', blank=True)
    created_by = models.ForeignKey(User)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)

    time_limit = models.IntegerField('Time limit per test', default=1000)
    sum_time_limit = models.IntegerField('Time limit all tests', default=10000)
    memory_limit = models.IntegerField('Memory limit', default=256)

    total_submit_number = models.IntegerField('Submit', default=0)
    total_accepted_number = models.IntegerField('Accepted', default=0)
