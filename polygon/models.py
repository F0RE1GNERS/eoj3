from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import RegexValidator
from django.db import models
from account.models import User
from problem.models import Problem
from utils.hash import sha_hash, case_hash
from utils.language import LANG_CHOICE

repo_storage = FileSystemStorage(location=settings.REPO_DIR)


class EditSession(models.Model):
  # DEPRECATED
  create_time = models.DateTimeField(auto_now_add=True)
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  fingerprint = models.CharField(max_length=64)
  problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
  last_synchronize = models.DateTimeField(blank=True)

  class Meta:
    ordering = ["-last_synchronize"]
    unique_together = ["user", "problem"]  # You can have only one session.


class Run(models.Model):
  # DEPRECATED
  STATUS_CHOICE = (
    (1, 'complete'),
    (0, 'running'),
    (-1, 'failed')
  )

  create_time = models.DateTimeField(auto_now_add=True)
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  status = models.IntegerField(choices=STATUS_CHOICE)
  label = models.TextField(blank=True)
  message = models.TextField(blank=True)


class NameValidator(RegexValidator):
  regex = r'^[A-Za-z0-9_-]{2,24}$'


class GroupNameValidator(RegexValidator):
  regex = r'^[A-Za-z0-9_-]{1,24}$'


class AliasValidator(RegexValidator):
  regex = r'^[a-z0-9]{2,30}$'
  message = 'Enter a valid alias. Use letters and digits only.'


class Statement(models.Model):
  """
  Statement: read only (create a new one when modified)
  """
  name = models.CharField("助记符", validators=[NameValidator()], max_length=24, default='default')
  title = models.CharField("题目标题", max_length=192)
  description = models.TextField("描述", blank=True)
  input = models.TextField("输入 / 交互约定", blank=True)
  output = models.TextField("输出", blank=True)
  hint = models.TextField("提示", blank=True)
  create_time = models.DateTimeField()
  update_time = models.DateTimeField(auto_now=True)
  parent_id = models.IntegerField(default=0)


class Asset(models.Model):
  """
  Asset: read only (create a new one when modified)
  """
  name = models.CharField("助记符", validators=[NameValidator()], max_length=24)
  file = models.FileField("文件", upload_to='assets/%Y%m%d/', storage=repo_storage)
  real_path = models.CharField(blank=True, max_length=192)
  create_time = models.DateTimeField()
  update_time = models.DateTimeField(auto_now=True)
  parent_id = models.IntegerField(default=0)


class Program(models.Model):
  """
  Program: read only (create a new one when modified)
  """
  LANG_CHOICES = (
    ('cpp', 'C++11'),
    ('cc14', 'C++14'),
    ('java', 'Java'),
    ('python', 'Python')
  )

  TAG_CHOICES = (
    ('checker', '输出校验'),
    ('interactor', '交互程序'),
    ('generator', '生成器'),
    ('validator', '输入校验'),
    ('solution_main', '解答 - 标准答案'),
    ('solution_correct', '解答 - 正确'),
    ('solution_tle_or_ok', '解答 - 超时或正确'),
    ('solution_wa', '解答 - 输出答案错误'),
    ('solution_incorrect', '解答 - 不正确'),
    ('solution_fail', '解答 - 运行时错误'),
    ('useless', '没用的')
  )

  name = models.CharField("名称", validators=[NameValidator()], max_length=24)
  lang = models.CharField("语言", choices=LANG_CHOICES, default='cc14', max_length=12)
  code = models.TextField("代码", blank=True)
  tag = models.CharField("标记为", choices=TAG_CHOICES, default='checker', max_length=24)
  create_time = models.DateTimeField()
  update_time = models.DateTimeField(auto_now=True)
  fingerprint = models.CharField(max_length=64)
  parent_id = models.IntegerField(default=0)

  def save_fingerprint(self):
    self.fingerprint = sha_hash(sha_hash(self.lang) + sha_hash(self.code) + sha_hash(self.tag))

  def save(self, **kwargs):
    self.save_fingerprint()
    super().save(**kwargs)


class Case(models.Model):
  """
  Case: create a new one when modified (without duplicated in and out)
  If input and output are modified, then create new file for input and output
  """
  fingerprint = models.CharField("指纹", max_length=64, default='invalid')
  input_file = models.FileField("输入文件", upload_to='cases/%Y%m%d/', storage=repo_storage)
  output_file = models.FileField("输出文件", upload_to='cases/%Y%m%d/', storage=repo_storage)
  in_samples = models.BooleanField("加入样例", default=False)
  in_pretests = models.BooleanField("加入 Pretests", default=False)
  points = models.PositiveIntegerField("分值", default=10)
  output_lock = models.BooleanField("锁定输出内容", default=False)
  description = models.TextField("描述", blank=True)
  case_number = models.PositiveIntegerField("测试点编号", default=1)
  create_time = models.DateTimeField()
  update_time = models.DateTimeField(auto_now=True)
  activated = models.BooleanField("加入测试数据", default=True)
  parent_id = models.IntegerField(default=0)
  group = models.PositiveIntegerField("分组编号", default=0)

  def save_fingerprint(self, problem_id):
    self.input_file.seek(0)
    self.output_file.seek(0)
    self.fingerprint = case_hash(problem_id, self.input_file.read(), self.output_file.read())

  @staticmethod
  def _read_file_preview(file):
    file.seek(0)
    p = file.read(20)
    try:
      p = p.decode().strip()
      if file.read(1):
        p += "..."
      return p
    except UnicodeDecodeError:
      return p

  @property
  def input_preview(self):
    return self._read_file_preview(self.input_file)

  @property
  def output_preview(self):
    return self._read_file_preview(self.output_file)


class Template(models.Model):
  template_code = models.TextField("模板代码")
  grader_code = models.TextField("评分代码")
  language = models.CharField("语言", max_length=12, choices=LANG_CHOICE, default='cpp')
  create_time = models.DateTimeField()
  update_time = models.DateTimeField(auto_now=True)
  parent_id = models.IntegerField(default=0)


class Revision(models.Model):
  STATUS_CHOICE = (
    (-1, '已终止'),
    (0, '正在编辑'),
    (1, '已完成')
  )

  problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='revisions')
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  revision = models.PositiveIntegerField()
  statements = models.ManyToManyField(Statement)
  programs = models.ManyToManyField(Program)
  cases = models.ManyToManyField(Case)
  assets = models.ManyToManyField(Asset)
  templates = models.ManyToManyField(Template)
  active_statement = models.ForeignKey(Statement, on_delete=models.SET_NULL, related_name="stating_revisions",
                                       null=True)
  active_checker = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="checking_revisions", null=True)
  active_validator = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="validating_revisions",
                                       null=True)
  active_interactor = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="interacting_revisions",
                                        null=True)
  messages = models.TextField(default='[]')  # json
  create_time = models.DateTimeField(auto_now_add=True)
  update_time = models.DateTimeField(auto_now=True)
  time_limit = models.PositiveIntegerField("时限 (ms)", default=2000)
  memory_limit = models.PositiveIntegerField("内存限制 (MB)", default=256)
  well_form_policy = models.BooleanField("对测试数据中的空白、换行、不可见字符进行自动处理", default=True)
  status = models.IntegerField("状态", choices=STATUS_CHOICE, default=0)
  parent_id = models.IntegerField(default=0)
  enable_group = models.BooleanField("启用捆绑测试", default=False)
  group_count = models.PositiveIntegerField("分组数量", default=0)
  group_dependencies = models.TextField("分组间依赖关系", blank=True)
  # group dependencies in the same format as in group format
  group_points = models.TextField("分组分值", blank=True)

  # when a revision is done, making changes will create a new revision

  class Meta:
    unique_together = ('problem', 'revision')


class Task(models.Model):
  STATUS_CHOICE = (
    (-3, 'PENDING'),
    (-2, 'RUNNING'),
    (-1, 'FAILED'),
    (0, 'OK'),
    (1, 'ABORTED')
  )

  revision = models.ForeignKey(Revision, on_delete=models.CASCADE)
  abstract = models.TextField(blank=True, max_length=256)
  status = models.IntegerField(choices=STATUS_CHOICE, default=-3)
  report = models.TextField(blank=True)
  create_time = models.DateTimeField(auto_now_add=True)
  update_time = models.DateTimeField(auto_now=True)


class FavoriteProblem(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="polygon_favorite_problems")
  problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="polygon_problems_favorite_by")
  create_time = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('user', 'problem')


class Package(models.Model):
  created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
  create_time = models.DateTimeField(auto_now_add=True)


class CodeforcesPackage(Package):
  dir_name = models.CharField(max_length=64)
  remote_problem_id = models.CharField(max_length=64)
  status = models.IntegerField(default=-1, choices=(
    (-1, 'Pending'),
    (0, 'OK'),
    (1, 'Failed')
  ))
  running_time = models.FloatField(null=True)
  short_name = models.CharField(null=True, blank=True, max_length=192)
  revision = models.IntegerField(null=True)
  size = models.FloatField(null=True)
