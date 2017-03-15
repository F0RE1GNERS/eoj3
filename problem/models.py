from django.db import models
from account.models import User


class Problem(models.Model):
    title = models.CharField('Title', max_length=128, blank=True)
    description = models.TextField('Description', blank=True)
    source = models.CharField('Source', max_length=128, blank=True)
    created_by = models.ForeignKey(User)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)

    time_limit = models.IntegerField('Time limit per test', default=1000)
    sum_time_limit = models.IntegerField('Time limit all tests', default=10000)
    memory_limit = models.IntegerField('Memory limit', default=256)
    judge = models.CharField('Judge indicator', blank=True)

    total_submit_number = models.IntegerField('Submit', default=0)
    total_accepted_number = models.IntegerField('Accepted', default=0)

    testdata_hash = models.CharField('Testdata zip hash value', max_length=64, blank=True)

    def __str__(self):
        return '%d - %s' % (self.pk, self.title)
