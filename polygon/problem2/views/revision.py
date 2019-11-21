import json
import os
from datetime import datetime
from shutil import copyfile

from django.conf import settings
from django.contrib import messages
from django.core.files import File
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView

from dispatcher.models import Server
from dispatcher.models import ServerProblemStatus
from polygon.models import Revision
from polygon.problem2.forms import RevisionUpdateForm
from polygon.problem2.views.base import ProblemRevisionMixin, PolygonProblemMixin
from problem.models import SpecialProgram, get_input_path, get_output_path
from problem.tasks import upload_problem_to_judge_server
from problem.views import StatusList
from submission.models import Submission


class RevisionCreateView(PolygonProblemMixin, View):
  """
  Directly create a revision from an online problem
  """

  @staticmethod
  def keep_first_occurrence(lst):
    ret, track = [], set()
    for t in lst:
      if t not in track:
        track.add(t)
        ret.append(t)
    return ret

  @transaction.atomic()
  def post(self, *args, **kwargs):
    if self.problem.revisions.all().count():
      revision_num = self.problem.revisions.all().aggregate(Max("revision"))["revision__max"] + 1
    else:
      revision_num = 1
    revision = Revision.objects.create(problem=self.problem,
                                       user=self.request.user,
                                       revision=revision_num,
                                       time_limit=self.problem.time_limit,
                                       memory_limit=self.problem.memory_limit)
    if self.problem.title or self.problem.description or self.problem.input or \
        self.problem.output or self.problem.hint:
      statement = revision.statements.create(description=self.problem.description,
                                             input=self.problem.input,
                                             output=self.problem.output,
                                             hint=self.problem.hint,
                                             title=self.problem.title,
                                             create_time=datetime.now())
      revision.active_statement = statement
    for t in ("checker", "validator", "interactor"):
      fingerprint = getattr(self.problem, t)
      if not fingerprint:
        continue
      program = SpecialProgram.objects.get(fingerprint=fingerprint)
      created_program = revision.programs.create(name=program.filename,
                                                 lang=program.lang,
                                                 code=program.code,
                                                 tag=program.category,
                                                 create_time=datetime.now())
      setattr(revision, 'active_%s' % t, created_program)

    asset_base_dir = os.path.join(settings.UPLOAD_DIR, str(self.problem.id))
    if os.path.exists(asset_base_dir):
      asset_files = os.listdir(asset_base_dir)
      for file in asset_files:
        file_path = os.path.join(asset_base_dir, file)
        with open(file_path, 'rb') as file_reader:
          ref_name = file[:file.find('.')] if '.' in file else file
          asset = revision.assets.create(name=ref_name,
                                         real_path='/upload/%d/%s' % (self.problem.id, file),
                                         create_time=datetime.now())
          asset.file.save(file, File(file_reader))

    cases_to_copy = self.keep_first_occurrence(
      self.problem.sample_list + self.problem.pretest_list + self.problem.case_list)
    if self.problem.group_enabled:
      case_to_pts = dict()
      group_list = self.problem.group_list
      revision.enable_group = True
      revision.group_points = self.problem.points
      revision.group_count = max(group_list)
      revision.group_dependencies = self.problem.group_config
    else:
      case_to_pts = dict(zip(self.problem.case_list, self.problem.point_list))
      group_list = [0] * len(self.problem.case_list)
    loc = 0
    for idx, fingerprint in enumerate(cases_to_copy, start=1):
      input_path, output_path = get_input_path(fingerprint), get_output_path(fingerprint)
      with open(input_path, "rb") as inf, open(output_path, "rb") as ouf:
        case = revision.cases.create(fingerprint=fingerprint,
                                     in_samples=fingerprint in self.problem.sample_list,
                                     in_pretests=fingerprint in self.problem.pretest_list,
                                     activated=fingerprint in self.problem.case_list,
                                     points=int(case_to_pts.get(fingerprint, 0)),
                                     case_number=idx,
                                     create_time=datetime.now(),
                                     group=group_list[loc])
        case.input_file.save("input", File(inf))
        case.output_file.save("output", File(ouf))
      if fingerprint in self.problem.case_list:
        loc += 1

    for language, item in self.problem.template_dict.items():
      revision.templates.create(language=language,
                                template_code=item["template"],
                                grader_code=item["grader"],
                                create_time=datetime.now())

    revision.save()

    return redirect(reverse('polygon:revision_update', kwargs={"pk": self.problem.pk, "rpk": revision.pk}))


class RevisionForkView(ProblemRevisionMixin, View):
  """
  Fork a previous revision into a new one
  """
  post_allowed_for_low_permission = True

  @transaction.atomic()
  def post(self, *args, **kwargs):
    old_revision = Revision.objects.get(pk=self.revision.pk)
    self.revision.parent_id = old_revision.id
    self.revision.id = None
    self.revision.revision = self.problem.revisions.all().aggregate(Max("revision"))["revision__max"] + 1
    self.revision.user = self.request.user
    self.revision.status = 0
    self.revision.save()
    self.revision.statements.add(*old_revision.statements.all())
    self.revision.assets.add(*old_revision.assets.all())
    self.revision.programs.add(*old_revision.programs.all())
    self.revision.cases.add(*old_revision.cases.all())
    self.revision.templates.add(*old_revision.templates.all())
    self.revision.task_set.add(*old_revision.task_set.all())
    self.kwargs.update(rpk=self.revision.id)
    return redirect(reverse('polygon:revision_update', kwargs=self.kwargs))


class RevisionUpdateView(ProblemRevisionMixin, UpdateView):
  form_class = RevisionUpdateForm
  template_name = 'polygon/problem2/revision/update.jinja2'
  polygon_title = "概览"

  def get_object(self, queryset=None):
    return self.revision

  def get_success_url(self):
    return self.request.path

  def get_context_data(self, **kwargs):
    """
    Index page of revision
    """
    data = super().get_context_data(**kwargs)
    data["revision_list"] = self.problem.revisions.select_related("user").order_by("-revision").all()
    pk_to_revision = {revision.pk: revision.revision for revision in data["revision_list"]}
    for revision in data["revision_list"]:
      revision.based_on = pk_to_revision.get(revision.parent_id)
    return data


class RevisionConfirmView(ProblemRevisionMixin, View):
  """
  Confirm current revision and publish it online and to judge servers
  """

  @transaction.atomic()
  def post(self, request, *args, **kwargs):
    if self.errors:
      return HttpResponse()
    for attr in ("title", "description", "input", "output", "hint"):
      setattr(self.problem, attr, getattr(self.revision.active_statement, attr))
    for t in ("checker", "validator", "interactor"):
      program = getattr(self.revision, "active_%s" % t)
      if program is None:
        setattr(self.problem, t, '')
      else:
        try:
          SpecialProgram.objects.get(fingerprint=program.fingerprint)
        except SpecialProgram.DoesNotExist:
          SpecialProgram.objects.create(fingerprint=program.fingerprint,
                                        lang=program.lang,
                                        filename=program.name,
                                        category=program.tag,
                                        code=program.code)
        setattr(self.problem, t, program.fingerprint)

    samples, pretests, tests, points = [], [], [], []
    case_prep = [[] for i in range(self.revision.group_count)]
    for case in self.revision.cases.all().order_by("case_number"):
      if case.in_samples:
        samples.append(case.fingerprint)
      if case.in_pretests:
        pretests.append(case.fingerprint)
      if case.activated:
        tests.append(case.fingerprint)
        points.append(case.points)
      problem_case_input, problem_case_output = get_input_path(case.fingerprint), get_output_path(case.fingerprint)
      if not os.path.exists(problem_case_input):
        copyfile(case.input_file.path, problem_case_input)
        copyfile(case.output_file.path, problem_case_output)
      if self.revision.enable_group:
        case_prep[case.group - 1].append(case.fingerprint)

    if self.revision.enable_group:
      self.problem.cases = ';'.join([','.join(x) for x in case_prep])
      self.problem.points = self.revision.group_points
      self.problem.group_config = self.revision.group_dependencies
    else:
      self.problem.cases = ','.join(tests)
      self.problem.points = ','.join(map(str, points))
      self.problem.group_config = '~'  # ~ means nothing here, since nothing is already taken...
    self.problem.pretests = ','.join(pretests)
    self.problem.sample = ','.join(samples)

    template_dict = {template.language: {
      "template": template.template_code,
      "grader": template.grader_code
    } for template in self.revision.templates.all()}
    self.problem.template_config = json.dumps(template_dict)

    self.problem.time_limit = self.revision.time_limit
    self.problem.memory_limit = self.revision.memory_limit

    try:
      for server in Server.objects.filter(enabled=True).all():
        upload_problem_to_judge_server(self.problem, server)
        status, _ = ServerProblemStatus.objects.get_or_create(problem=self.problem, server=server)
        status.save()
        server.last_synchronize_time = datetime.now()
        server.save(update_fields=['last_synchronize_time'])
      self.problem.save()
      self.revision.status = 1
      self.revision.save(update_fields=["status"])
    except Exception as e:
      messages.error(self.request, "Upload failed: " + str(e))
    return redirect(reverse('polygon:revision_update', kwargs=self.kwargs))


class RevisionDiscardView(ProblemRevisionMixin, View):
  """
  Discard current revision
  """

  @transaction.atomic()
  def post(self, request, *args, **kwargs):
    self.revision.status = -1
    self.revision.save(update_fields=["status"])
    return redirect(reverse('polygon:revision_update', kwargs=self.kwargs))


class RevisionStatus(ProblemRevisionMixin, StatusList):
  template_name = 'polygon/problem2/status.jinja2'
  privileged = True
  polygon_title = "提交记录"

  def get_selected_from(self):
    return Submission.objects.filter(problem_id=self.problem.id)
