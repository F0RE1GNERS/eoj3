import json
import re
from os import path, makedirs

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from tagging.registry import register

from account.models import User
from submission.util import SubmissionStatus
from utils.language import LANG_CHOICE


class AliasValidator(RegexValidator):
  regex = r'^[a-z0-9]{2,30}$'
  message = _(
    'Enter a valid alias. Use letters and digits only.'
  )


class Problem(models.Model):
  alias_validator = AliasValidator()
  alias = models.CharField(_('Alias'), max_length=64, blank=True, validators=[alias_validator])

  # generate
  title = models.CharField(_('Title'), max_length=192, blank=True)

  description = models.TextField(_('Description'), blank=True)
  input = models.TextField(_('Input'), blank=True)
  output = models.TextField(_('Output'), blank=True)
  sample = models.TextField(_('Sample'), blank=True)
  hint = models.TextField(_('Hint'), blank=True)

  source = models.CharField(_('Source'), max_length=128, blank=True)

  visible = models.BooleanField(default=False, db_index=True)
  maintaining = models.BooleanField(default=False)
  create_time = models.DateTimeField(auto_now_add=True)
  update_time = models.DateTimeField()

  time_limit = models.IntegerField(_('Time Limit'), default=2000)
  memory_limit = models.IntegerField(_('Memory Limit'), default=256)
  checker = models.CharField(_('Checker'), blank=True, max_length=64)
  interactor = models.CharField(_('Interactor'), blank=True, max_length=64)

  # If you see this, you will realize that there are a lot more we attempted to do,
  # but they didn't end very well; and in the end I don't know what I was thinking in the first place,
  # and I want to say thank you for looking into this.
  validator = models.CharField(_('Validator'), blank=True, max_length=64)
  pretests = models.TextField(_('Pretest'), blank=True)
  clone_parent = models.PositiveIntegerField(default=0)
  # ABANDONED FIELDS END

  cases = models.TextField(_('Cases'), blank=True)
  points = models.TextField(_('Points'), blank=True)
  group_config = models.TextField(_('Group'), blank=True, default='~')
  # group config in the following format: 1,2;2,3;3,4 (index 1 based)
  # leave this blank to ignore groups
  template_config = models.TextField(_('Template'), blank=True, default='{}')

  level = models.IntegerField(_('Difficulty Level'), choices=(
    (1, 'Naive'),
    (2, 'Easy'),
    (3, 'Medium'),
    (4, 'Hard'),
    (5, 'Super')
  ), default=3)

  managers = models.ManyToManyField(User, related_name='managing_problems')

  ac_user_count = models.PositiveIntegerField(default=0)
  total_user_count = models.PositiveIntegerField(default=0)
  ac_count = models.PositiveIntegerField(default=0)
  total_count = models.PositiveIntegerField(default=0)
  reward = models.FloatField(default=9.9)


  def save(self, *args, **kwargs):
    self.update_time = timezone.now()
    return super(Problem, self).save(*args, **kwargs)

  def __str__(self):
    return '%d. %s' % (self.pk, self.title)

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
    return list(filter(lambda x: x, re.split(r"[,;]", self.cases)))

  @property
  def template_dict(self):
    try:
      return json.loads(self.template_config)
    except:
      return dict()

  @property
  def group_list(self):
    if not self.cases:
      return []
    # be rigid and careful because group list generation here does not consider spaces or extra punctuations
    punc = list(filter(lambda x: x in ",;", self.cases + ";"))
    now, ret = 1, []
    for p in punc:
      ret.append(now)
      if p == ';':
        now += 1
    if len(ret) != len(self.case_list):
      raise AssertionError("Group list should have the same length as case list")
    return ret

  @property
  def group_dependencies(self):
    return list(map(lambda x: tuple(map(int, x.split(","))),
                    filter(lambda x: x, self.group_config.split(";"))))

  @property
  def group_enabled(self):
    return self.group_config != "~"

  @property
  def point_list(self):
    return list(
      map(int, list(filter(lambda x: x, self.points.split(',')))))  # point list should be as long as case list

  @property
  def sample_display(self):
    return [get_input_and_output_for_case(case) for case in self.sample_list]

  def _status_count(self, status):
    return self.submission_set.filter(status=status, visible=True).values("id").count()

  @property
  def ac_user_ratio(self):
    return self.ac_user_count / self.total_user_count if self.total_user_count > 0 else 0.0

  @property
  def ac_ratio(self):
    return self.ac_count / self.total_count if self.total_count > 0 else 0.0

  @property
  def stats(self):
    ret = {
      "ac": self.ac_count,
      "wa": self._status_count(SubmissionStatus.WRONG_ANSWER),
      "tle": self._status_count(SubmissionStatus.TIME_LIMIT_EXCEEDED),
      "re": self._status_count(SubmissionStatus.RUNTIME_ERROR),
      "ce": self._status_count(SubmissionStatus.COMPILE_ERROR)
    }
    ret["others"] = self.total_count - sum(ret.values())
    return ret


register(Problem)


class ProblemRewardStatus(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  problem = models.ForeignKey(Problem, on_delete=models.CASCADE)

  class Meta:
    unique_together = ('user', 'problem')


class SpecialProgram(models.Model):
  CATEGORIES = ((x, x) for x in ('checker', 'generator', 'interactor', 'validator'))

  fingerprint = models.CharField(max_length=64, primary_key=True)
  category = models.CharField(max_length=12, choices=CATEGORIES)
  filename = models.CharField(max_length=64)
  lang = models.CharField('language', max_length=12, choices=LANG_CHOICE, default='cc14')
  code = models.TextField(blank=True)
  builtin = models.BooleanField(default=False)

  def __str__(self):
    return '%s (%s)' % (self.filename, self.category.capitalize())


def _get_data_path(category, hash):
  parts = [settings.TESTDATA_DIR, category]
  if len(hash) >= 2:
    parts.append(hash[:2])
  else:
    parts.append("??")
  if len(hash) >= 4:
    parts.append(hash[2:4])
  else:
    parts.append("??")
  directory = path.join(*parts)
  makedirs(directory, exist_ok=True)
  parts.append(hash)
  return path.join(*parts)


def get_input_path(case_hash):
  return _get_data_path("in", case_hash)


def get_output_path(case_hash):
  return _get_data_path("out", case_hash)


def get_input_and_output_for_case(case_hash):
  """
  :type case_hash: str
  :return: (input_data, output_data)
  """
  with open(get_input_path(case_hash), 'r') as inf:
    input_data = inf.read()
  with open(get_output_path(case_hash), 'r') as ouf:
    output_data = ouf.read()
  return (input_data, output_data)
