import io
import json
import re
import shutil
import zipfile
from datetime import datetime
from os import path

import chardet
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile, File
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView

from polygon.models import Case
from polygon.problem2.forms import CaseUpdateForm, CaseCreateForm, CaseUpdateInfoForm
from polygon.problem2.views.base import ProblemRevisionMixin
from utils import random_string
from utils.download import respond_generate_file
from utils.file_preview import sort_data_list_from_directory


CASE_SUM_MAX_TOTAL_LENGTH = 2048 * 1024 * 1024


class UpdateManager(object):
  def __init__(self, object, revision):
    self.object = object
    self.revision = revision

  def __enter__(self):
    if self.object.revision_set.all().count() > 1:
      # the case is related to a revision other than this one
      with transaction.atomic():
        # only for cases now
        self.revision.cases.remove(self.object)
        self.object.parent_id = self.object.pk
        self.object.pk = None
        self.object.save()
        self.revision.cases.add(self.object)
    return self.object

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.object.save()


class CaseManagementTools(object):
  white_space_reg = re.compile(r'[\x00-\x20\s]+')

  @staticmethod
  def read_by_formed_lines(fileobj):
    for line in fileobj:
      yield ' '.join(CaseManagementTools.white_space_reg.split(line.strip()))

  @staticmethod
  def well_form_text(text):
    stream = io.StringIO(text.strip())
    out_stream = io.StringIO()
    for line in CaseManagementTools.read_by_formed_lines(stream):
      out_stream.writelines([line, '\n'])
    out_stream.seek(0)
    return out_stream.read()

  @staticmethod
  def well_form_binary(binary):
    try:
      encoding = chardet.detect(binary).get('encoding', 'utf-8')
      return CaseManagementTools.well_form_text(binary.decode(encoding))
    except:
      return ''

  @staticmethod
  def reformat(txt, well_form_policy=True):
    if isinstance(txt, str):
      txt = txt.encode()
    if well_form_policy:
      return CaseManagementTools.well_form_binary(txt)
    else:
      return txt

  @staticmethod
  def reformat_file(file_path, well_form_policy=True):
    if well_form_policy:
      with open(file_path, "rb+") as file_obj:
        file_obj.seek(0)
        ret = CaseManagementTools.reformat(file_obj.read())
        file_obj.seek(0)
        file_obj.truncate(0)
        file_obj.write(ret.encode())

  @staticmethod
  def naturalize_order(revision, case_set):
    with transaction.atomic():
      for idx, case in enumerate(case_set, start=1):
        if idx != case.case_number:
          with UpdateManager(case, revision) as t:
            t.case_number = idx

  @staticmethod
  def read_abstract(file_path, read_size=1024):
    try:
      with open(file_path, "r") as f:
        t = f.read(read_size + 1)
      if len(t) > read_size:
        return t[:read_size] + '...'
      return t
    except FileNotFoundError:
      return ''


REFORMAT = CaseManagementTools.reformat
NATURALIZE_ORDER = CaseManagementTools.naturalize_order


class RevisionCaseMixin(ProblemRevisionMixin):
  model_class = Case

  def init_revision(self, *args, **kwargs):
    super().init_revision(*args, **kwargs)
    if not self.verify_belong_to_revision(kwargs['cpk']):
      raise Http404("No cases found matching the query")
    self.case = Case.objects.get(pk=kwargs['cpk'])


class RevisionMultipleCasesMixin(ProblemRevisionMixin):

  def init_revision(self, *args, **kwargs):
    super().init_revision(*args, **kwargs)
    self.pk_set = set(filter(lambda x: x, self.request.POST["gather"].split(",")))
    if not self.pk_set:
      raise ValueError("Invalid selected cases")
    self.case_set = self.revision.cases.filter(pk__in=self.pk_set).order_by("case_number")
    if len(self.case_set) != len(self.pk_set):
      raise ValueError("Invalid selected cases")

  def get_redirect_url(self):
    return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})


class CaseList(ProblemRevisionMixin, ListView):
  template_name = 'polygon/problem2/case/list.jinja2'
  context_object_name = 'case_list'
  polygon_title = "数据管理"

  def get_queryset(self):
    qs = self.revision.cases.all().order_by("case_number")
    for case in qs:
      case.comments = []
      if case.description:
        case.comments.append(case.description)
      if case.in_samples:
        case.comments.append("属于样例.")
      if not case.activated:
        case.comments.append("不在最终测试数据中.")
      if not self.revision.enable_group:
        case.comments.append("计 %d 分." % case.points)
    return qs

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    if not data['revision_readonly']:
      data["disable_grid"] = True
    return data


class CaseCreateView(ProblemRevisionMixin, FormView):
  form_class = CaseCreateForm
  template_name = 'polygon/problem2/case/create.jinja2'
  polygon_title = "添加数据"

  def get_success_url(self):
    return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

  def form_valid(self, form):
    global_create_time = datetime.now()
    option = form.cleaned_data["option"]
    case_number_start = form.cleaned_data["case_number"]
    cases = []
    current_total_size = self.get_current_total_size()

    if option == "text":
      input_binary = REFORMAT(form.cleaned_data["input_text"].encode(), self.revision.well_form_policy)
      output_binary = REFORMAT(form.cleaned_data["output_text"].encode(), self.revision.well_form_policy)
      description = "手动创建."
      case = Case(create_time=global_create_time,
                  in_samples=form.cleaned_data["in_samples"],
                  description=description,
                  activated=form.cleaned_data["activated"])
      case.input_file.save("in", ContentFile(input_binary), save=False)
      case.output_file.save("out", ContentFile(output_binary), save=False)
      case.save_fingerprint(self.problem.id)
      if current_total_size + case.case_size > CASE_SUM_MAX_TOTAL_LENGTH:
        raise ValueError("测试点总规模已超过限制 (2GB)")
      cases.append(case)

    elif option == "batch":
      tmp_directory = '/tmp/' + random_string()
      with zipfile.ZipFile(form.cleaned_data["batch_file"]) as myZip:
        myZip.extractall(path=tmp_directory)
      case_config = {}
      if path.exists(path.join(tmp_directory, "data.json")):
        with open(path.join(tmp_directory, "data.json")) as json_config:
          case_config = json.loads(json_config.read())
      for inf, ouf in sort_data_list_from_directory(tmp_directory):
        with open(path.join(tmp_directory, inf), 'rb') as ins, open(path.join(tmp_directory, ouf),
                                                                    'rb') as ous:
          conf = case_config.get(inf, {})
          case = Case(create_time=global_create_time,
                      description=conf.get("description", "\"%s\": (%s, %s)." %
                                           (form.cleaned_data["batch_file"].name, inf, ouf)),
                      in_samples=conf.get("in_samples", False),
                      activated=conf.get("activated", True),
                      group=conf.get("group", 0),
                      points=conf.get("points", 10))
          if self.revision.well_form_policy:
            case.input_file.save("in", ContentFile(REFORMAT(ins.read(), True)), save=False)
            case.output_file.save("out", ContentFile(REFORMAT(ous.read(), True)), save=False)
          else:
            case.input_file.save("in", File(ins), save=False)
            case.output_file.save("out", File(ous), save=False)
          case.save_fingerprint(self.problem.id)
          if current_total_size + case.case_size > CASE_SUM_MAX_TOTAL_LENGTH:
            raise ValueError("测试点总规模已超过限制 (2GB)")
          current_total_size += case.case_size
          cases.append(case)
      shutil.rmtree(tmp_directory)

    # process case numbers
    remove_list = []
    if case_number_start <= 0:
      # auto fill the empty indices
      idx = 1
      exist = set(self.revision.cases.all().values_list("case_number", flat=True))
      for case in cases:
        while idx in exist:
          idx += 1
        exist.add(idx)
        case.case_number = idx
    else:
      idx = case_number_start
      for case in cases:
        case.case_number = idx
        idx += 1
      for case in self.revision.cases.filter(case_number__gte=case_number_start).order_by("case_number"):
        # do modifications to modified cases
        if idx != case.case_number:
          case.case_number = idx
          idx += 1
          case.parent_id = case.id
          remove_list.append(Case(pk=case.id))
          case.id = None
          cases.append(case)

    with transaction.atomic():
      for case in cases:
        case.save()
      self.revision.cases.add(*cases)
      self.revision.cases.remove(*remove_list)

    messages.success(self.request, "%d 组数据已成功添加." % len(cases))

    return redirect(self.get_success_url())


class CaseUpdateFileView(RevisionCaseMixin, FormView):
  form_class = CaseUpdateForm
  template_name = 'polygon/problem2/case/update.jinja2'
  polygon_title = "更新数据"

  def get_success_url(self):
    return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

  def get_object(self):
    return self.case

  def form_valid(self, form):
    current_total_size = self.get_current_total_size()
    with transaction.atomic():
      obj = self.get_object()
      input_binary = REFORMAT(form.cleaned_data["input_text"].encode(), self.revision.well_form_policy)
      output_binary = REFORMAT(form.cleaned_data["output_text"].encode(), self.revision.well_form_policy)
      with UpdateManager(obj, self.revision) as obj:
        obj.input_file.save("in", ContentFile(input_binary), save=False)
        obj.output_file.save("out", ContentFile(output_binary), save=False)
        obj.save_fingerprint(self.problem.id)
      if current_total_size + obj.case_size > CASE_SUM_MAX_TOTAL_LENGTH:
        raise ValueError("测试点总规模已超过限制 (2GB)")
    return redirect(self.get_success_url())


class CaseUpdateInfoView(RevisionCaseMixin, UpdateView):
  form_class = CaseUpdateInfoForm
  template_name = 'polygon/problem2/simple_form.jinja2'
  polygon_title = "更新数据"

  def get_success_url(self):
    return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

  def get_object(self, queryset=None):
    return self.case

  def form_valid(self, form):
    with transaction.atomic():
      with UpdateManager(self.object, self.revision) as case:  # pylint: disable=unused-variable
        # probably buggy here, fix later
        case = form.save()
    return redirect(self.get_success_url())


class CaseDeleteView(RevisionCaseMixin, View):
  def post(self, request, *args, **kwargs):
    try:
      self.revision.cases.remove(self.case)
      return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
    except Case.DoesNotExist:
      raise Http404("No cases found matching the query")


class CaseFullInputOutputView(RevisionCaseMixin, View):
  def get(self, request, *args, **kwargs):
    if "t" not in request.GET or request.GET["t"].lower() not in ("input", "output"):
      return HttpResponseBadRequest()
    if request.GET["t"].lower() == "input":
      p = self.case.input_file.read()
    else:
      p = self.case.output_file.read()
    return HttpResponse(p, content_type="text/plain; charset=utf-8")


class CaseNaturalizeOrderView(ProblemRevisionMixin, View):
  def post(self, request, *args, **kwargs):
    if request.GET.get("group"):
      qs = self.revision.cases.all().order_by("group", "case_number")
      qs = list(filter(lambda x: x.group != 0, qs)) + list(filter(lambda x: x.group == 0, qs))
    else:
      qs = self.revision.cases.all().order_by("case_number")
    NATURALIZE_ORDER(self.revision, qs)
    return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CaseMoveOrderView(RevisionMultipleCasesMixin, View):
  def post(self, request, *args, **kwargs):
    after = int(request.POST.get("answer") or 0)
    other_case_set = self.revision.cases.exclude(pk__in=self.pk_set).order_by("case_number")
    insert_pos = 0
    while insert_pos < len(other_case_set) and other_case_set[insert_pos].case_number <= after:
      insert_pos += 1
    ret = other_case_set[:insert_pos] + list(self.case_set) + other_case_set[insert_pos:]
    NATURALIZE_ORDER(self.revision, ret)
    return redirect(self.get_redirect_url())


class CaseDeleteSelectedView(RevisionMultipleCasesMixin, View):
  def post(self, request, *args, **kwargs):
    self.revision.cases.remove(*list(self.case_set))
    NATURALIZE_ORDER(self.revision, self.revision.cases.all().order_by("case_number"))
    return redirect(self.get_redirect_url())


class CaseToggleSampleView(RevisionMultipleCasesMixin, View):
  def post(self, request, *args, **kwargs):
    for case in self.case_set:
      with UpdateManager(case, self.revision) as case:
        case.in_samples = not case.in_samples
    return redirect(self.get_redirect_url())


class CasePackAsZipView(ProblemRevisionMixin, View):
  def get_redirect_url(self):
    return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

  def get(self, request, *args, **kwargs):
    input_only = False
    if 'input' in request.GET:
      input_only = True
    cases = list(self.revision.cases.all().order_by("case_number"))
    if len(cases) == 0:
      messages.error(request, "There are no cases to pack.")
      return redirect(self.get_redirect_url())
    for idx, case in enumerate(cases):
      if idx > 0 and case.case_number == cases[idx - 1].case_number:
        messages.error(request, "Cases refuse to pack because there are two cases with the same case number.")
        return redirect(self.get_redirect_url())
    file_path = path.join(settings.GENERATE_DIR, random_string())
    case_config = {}
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip:
      for case in cases:
        zip.write(case.input_file.path, arcname="%d" % case.case_number)
        if not input_only:
          zip.write(case.output_file.path, arcname="%d.a" % case.case_number)
          case_config[str(case.case_number)] = {
            "in_samples": case.in_samples,
            "activated": case.activated,
            "group": case.group,
            "description": case.description,
            "points": case.points
          }
      if not input_only:
        zip.writestr("data.json", json.dumps(case_config, sort_keys=True, indent=2))

    return respond_generate_file(request, file_path,
                                 "TestData_%s#%d.zip" % (self.problem.alias, self.revision.revision))


class CaseAssignGroupView(RevisionMultipleCasesMixin, View):
  def post(self, request, *args, **kwargs):
    group_number = int(request.POST.get("answer") or 0)
    for case in self.case_set:
      with UpdateManager(case, self.revision) as case:
        case.group = group_number
    return redirect(self.get_redirect_url())
