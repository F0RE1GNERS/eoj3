from django.db import models
from django.conf import settings
from os import path
from account.models import User
from tagging.registry import register
from django.core.cache import cache
from utils.language import LANG_CHOICE


# This is the hash value of the famous fcmp.cpp
FCMP_FINGERPRINT = '3813d49afd13857026fcd4643f51689c39639f83c2b4136b8d95ed285510a00f'


class Problem(models.Model):

    alias = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=192, blank=True)
    description = models.TextField(blank=True)
    input = models.TextField(blank=True)
    output = models.TextField(blank=True)
    sample = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    source = models.CharField(max_length=128, blank=True)
    difficulty = models.FloatField(default=1500.0)

    visible = models.BooleanField(default=False)
    maintaining = models.BooleanField(default=False)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    time_limit = models.IntegerField(default=1000)
    memory_limit = models.IntegerField(default=256)
    checker = models.CharField(max_length=64, default=FCMP_FINGERPRINT)
    interactor = models.CharField(blank=True, max_length=64)
    validator = models.CharField(blank=True, max_length=64)
    pretests = models.TextField(blank=True)
    cases = models.TextField(blank=True)
    points = models.TextField(blank=True)

    manager = models.ManyToManyField(User, through='ProblemManagement')

    def __str__(self):
        return '%d - %s' % (self.pk, self.title)

    class Meta:
        ordering = ["-pk"]

    @property
    def sample_list(self):
        """
        sample name list
        """
        return list(filter(lambda x: x, self.sample.split(',')))

    @property
    def pretest_list(self):
        return list(filter(lambda x: x, self.pretests.split(',')))

    @property
    def case_list(self):
        return list(filter(lambda x: x, self.cases.split(',')))

    @property
    def point_list(self):
        return list(map(int, list(filter(lambda x: x, self.points.split(',')))))  # point list should be as long as case list

    def show_sample(self):
        return [get_input_and_output_for_case(case) for case in self.sample_list]


register(Problem)


class ProblemManagement(models.Model):
    PERMISSION_CHOICES = (
        ('a', 'ADMIN'),
        ('r', 'READ'),
        ('w', 'WRITE'),
    )

    problem = models.ForeignKey(Problem)
    user = models.ForeignKey(User)
    permission = models.CharField(max_length=2, choices=PERMISSION_CHOICES)

    class Meta:
        unique_together = ['problem', 'user']


class SpecialProgram(models.Model):

    CATEGORIES = ((x, x) for x in ('checker', 'generator', 'interactor', 'validator'))

    fingerprint = models.CharField(max_length=64, primary_key=True)
    category = models.CharField(max_length=12, choices=CATEGORIES)
    filename = models.CharField(max_length=64)
    lang = models.CharField('language', max_length=12, choices=LANG_CHOICE, default='cpp')
    code = models.TextField(blank=True)
    builtin = models.BooleanField(default=False)

    def __str__(self):
        return '%s (%s)' % (self.filename, self.category.capitalize())


def get_input_and_output_for_case(case_hash):
    """
    :type case_hash: str
    :return: (input_data, output_data)
    """
    with open(path.join(settings.TESTDATA_DIR, case_hash + '.in'), 'r') as inf:
        input_data = inf.read()
    with open(path.join(settings.TESTDATA_DIR, case_hash + '.out'), 'r') as ouf:
        output_data = ouf.read()
    return (input_data, output_data)


def get_input_path(case_hash):
    return path.join(settings.TESTDATA_DIR, case_hash + '.in')


def get_output_path(case_hash):
    return path.join(settings.TESTDATA_DIR, case_hash + '.out')