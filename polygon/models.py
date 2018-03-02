from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import RegexValidator
from django.db import models
from account.models import User
from problem.models import Problem
from utils.hash import sha_hash, case_hash

repo_storage = FileSystemStorage(location=settings.REPO_DIR)


class EditSession(models.Model):

    create_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    fingerprint = models.CharField(max_length=64)
    problem = models.ForeignKey(Problem)
    last_synchronize = models.DateTimeField(blank=True)

    class Meta:
        ordering = ["-last_synchronize"]
        unique_together = ["user", "problem"]  # You can have only one session.


class Run(models.Model):

    STATUS_CHOICE = (
        (1, 'complete'),
        (0, 'running'),
        (-1, 'failed')
    )

    create_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    status = models.IntegerField(choices=STATUS_CHOICE)
    label = models.TextField(blank=True)
    message = models.TextField(blank=True)


class NameValidator(RegexValidator):
    regex = r'^[A-Za-z0-9_-]{2,24}$'


class AliasValidator(RegexValidator):
    regex = r'^[a-z0-9]{2,30}$'
    message = 'Enter a valid alias. Use letters and digits only.'


class Statement(models.Model):
    """
    Statement: read only (create a new one when modified)
    """
    name = models.CharField(validators=[NameValidator()], max_length=24, default='default')
    title = models.CharField(max_length=192)
    description = models.TextField(blank=True)
    input = models.TextField(blank=True)
    output = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now=True)
    parent_id = models.IntegerField(default=0)


class Asset(models.Model):
    """
    Asset: read only (create a new one when modified)
    """
    name = models.CharField(validators=[NameValidator()], max_length=24)
    file = models.FileField(upload_to='assets/%Y%m%d/', storage=repo_storage)
    real_path = models.CharField(blank=True, max_length=192)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now=True)
    parent_id = models.IntegerField(default=0)


class Program(models.Model):
    """
    Program: read only (create a new one when modified)
    """
    LANG_CHOICES = (
        ('cpp', 'C++'),
        ('java', 'Java'),
        ('python', 'Python')
    )

    TAG_CHOICES = (
        ('checker', 'checker'),
        ('interactor', 'interactor'),
        ('generator', 'generator'),
        ('validator', 'validator'),
        ('solution_main', 'solution - main correct'),
        ('solution_correct', 'solution - correct'),
        ('solution_tle_or_ok', 'solution - time limit exceeded or correct'),
        ('solution_wa', 'solution - wrong answer'),
        ('solution_incorrect', 'solution - incorrect'),
        ('solution_fail', 'solution - runtime error'),
        ('useless', 'ignore me')
    )

    name = models.CharField(validators=[NameValidator()], max_length=24)
    lang = models.CharField(choices=LANG_CHOICES, default='cpp', max_length=12)
    code = models.TextField(blank=True)
    tag = models.CharField(choices=TAG_CHOICES, default='checker', max_length=24)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now=True)
    fingerprint = models.CharField(max_length=64)
    parent_id = models.IntegerField(default=0)

    def save(self, **kwargs):
        self.fingerprint = sha_hash(sha_hash(self.lang) + sha_hash(self.code) + sha_hash(self.tag))
        super().save(**kwargs)


class Case(models.Model):
    """
    Case: create a new one when modified (without duplicated in and out)
    If input and output are modified, then create new file for input and output
    """
    fingerprint = models.CharField(max_length=64, default='invalid')
    input_file = models.FileField(upload_to='cases/%Y%m%d/', storage=repo_storage)
    output_file = models.FileField(upload_to='cases/%Y%m%d/', storage=repo_storage)
    in_samples = models.BooleanField(default=False)
    in_pretests = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=10)
    output_lock = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    case_number = models.PositiveIntegerField(default=1)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now=True)
    activated = models.BooleanField(default=True)
    parent_id = models.IntegerField(default=0)

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


class Revision(models.Model):

    STATUS_CHOICE = (
        (-1, 'Discarded'),
        (0, 'Undergoing'),
        (1, 'Done')
    )

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='revisions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField()
    statements = models.ManyToManyField(Statement)
    programs = models.ManyToManyField(Program)
    cases = models.ManyToManyField(Case)
    assets = models.ManyToManyField(Asset)
    active_statement = models.ForeignKey(Statement, on_delete=models.SET_NULL, related_name="stating_revisions", null=True)
    active_checker = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="checking_revisions", null=True)
    active_validator = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="validating_revisions", null=True)
    active_interactor = models.ForeignKey(Program, on_delete=models.SET_NULL, related_name="interacting_revisions", null=True)
    messages = models.TextField(default='[]')  # json
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    time_limit = models.PositiveIntegerField(default=2000)
    memory_limit = models.PositiveIntegerField(default=256)
    well_form_policy = models.BooleanField(default=True)
    status = models.IntegerField(choices=STATUS_CHOICE, default=0)
    parent_id = models.IntegerField(default=0)

    # when a revision is done, making changes will create a new revision

    class Meta:
        unique_together = ('problem', 'revision')
