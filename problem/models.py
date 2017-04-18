from django.db import models
from account.models import User
from utils import markdown3
from tagging.registry import register


class Problem(models.Model):
    title = models.CharField('Title', max_length=192, blank=True)
    description = models.TextField('Description', blank=True)
    input = models.TextField('Input', blank=True)
    output = models.TextField('Output', blank=True)
    sample = models.TextField('Sample', blank=True)
    hint = models.TextField('Hint', blank=True)
    source = models.CharField('Source', max_length=128, blank=True)

    visible = models.BooleanField('Visible', default=False)
    create_time = models.DateTimeField('Created time', auto_now_add=True)

    time_limit = models.IntegerField('Time limit per test', default=1000)
    sum_time_limit = models.IntegerField('Time limit all tests', default=10000)
    memory_limit = models.IntegerField('Memory limit', default=256)
    judge = models.CharField('Judge indicator', max_length=128, blank=True)

    total_submit_number = models.IntegerField('Submit', default=0)
    total_accept_number = models.IntegerField('Accept', default=0)

    testdata_hash = models.CharField('Testdata zip hash value', max_length=64, blank=True)
    testdata_size = models.IntegerField('Number of testdata cases', default=1)

    def __str__(self):
        return '%d - %s' % (self.pk, self.title)

    def add_submit(self, add=1):
        self.total_submit_number += add

    def add_accept(self, add=1):
        self.total_accept_number += add

    def get_markdown(self):
        self.body = markdown3.convert(self.description)
        return self

    class Meta:
        ordering = ["-pk"]


register(Problem)