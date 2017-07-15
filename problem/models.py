from django.db import models
from account.models import User
from utils import markdown3
from tagging.registry import register
from django.core.cache import cache


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
    memory_limit = models.IntegerField('Memory limit', default=256)
    judge = models.CharField('Judge indicator', max_length=128, blank=True)

    manager = models.ManyToManyField(User, through='ProblemManagement')

    def __str__(self):
        return '%d - %s' % (self.pk, self.title)

    class Meta:
        ordering = ["-pk"]


register(Problem)


class ProblemManagement(models.Model):
    PERMISSION_CHOICES = (
        ('r', 'READ'),
        ('w', 'WRITE'),
        ('n', 'NONE'),
    )

    problem = models.ForeignKey(Problem)
    user = models.ForeignKey(User)
    permission = models.CharField(max_length=2, choices=PERMISSION_CHOICES)
