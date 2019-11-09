import os
import shutil
import traceback
import zipfile
from datetime import datetime
from xml.etree import ElementTree

from django import forms
from django.core.files.base import ContentFile
from django.db import transaction
from django.urls import reverse
from django.views.generic import FormView

from polygon.models import Revision, Program, Statement, Case
from polygon.problem2.views.base import ProblemRevisionMixin
from utils import random_string

LANGUAGE_ADAPTER = {
  "c.gcc": "c",
  "cpp.g++": "cpp",
  "cpp.g++11": "cpp",
  "cpp.g++14": "cc14",
  "cpp.g++17": "cc17",
  "cpp.ms": "cpp",
  "csharp.mono": "cs",
  "java7": "java",
  "java8": "java",
  "pas.dpr": "pas",
  "pas.fpc": "pas",
  "perl.5": "perl",
  "php.5": "php",
  "python.2": "py2",
  "python.3": "python",
  "rust": "rs",
  "scala": "scala"
}


class CodeforcesPackageAdapter:
  def __init__(self, directory: str, revision: Revision):
    self.directory = directory
    self.revision = revision

  def add_problem_option(self, name, value):
    if value is not None:
      setattr(self.revision, name, value)

  def update_info(self, time_limit=None, memory_limit=None, interactive=None):
    """
    Updates problem info
    :param time_limit: time limit in milliseconds or None if no update required
    :param memory_limit: memory limit in MB or None if no update required
    :param interactive: boolean, if problem is interactive, or None if no update required
    :returns boolean, if updated
    """
    self.add_problem_option('time_limit', time_limit)
    self.add_problem_option('memory_limit', memory_limit)
    return True

  def set_utility_file(self, path, lang, name):
    with open(os.path.join(self.directory, path), "r") as f:
      code = f.read()
    lang = LANGUAGE_ADAPTER[lang]
    sp = Program.objects.create(name="pkg_" + name, lang=lang, code=code, tag=name,
                                create_time=datetime.now())
    self.revision.programs.add(sp)
    self.add_problem_option("active_" + name + "_id", sp.id)

  def save_statement_from_file(self, filepath, encoding, language):
    with open(filepath, 'r', encoding=encoding) as statement_file:
      content = statement_file.read()
    statement = Statement(name="pkg_statement", create_time=datetime.now())
    statement.title = content[len('\\begin{problem}{'):content.find('}', len('\\begin{problem}{'))]
    content = content[content.find('\n') + 1:]
    input_format_start = content.find('\\InputFile')
    statement.description = content[:input_format_start]
    content = content[input_format_start:]
    content = content[content.find('\n') + 1:]
    output_format_start = content.find('\\OutputFile')
    statement.input = content[:output_format_start]
    content = content[output_format_start:]
    content = content[content.find('\n') + 1:]
    statement.output = content[:content.find('\\Example')]
    notes_start_pos = content.find('\\Note')
    if notes_start_pos >= 0:
      content = content[notes_start_pos:]
      content = content[content.find('\n') + 1:]
      statement.hint = content[:content.find('\\end{problem}')]
    statement.save()
    self.revision.statements.add(statement)
    self.add_problem_option("active_statement_id", statement.id)
    return True

  def save_statement(self, statement_node):
    if not statement_node.attrib['type'].endswith('tex'):
      return
    return self.save_statement_from_file(os.path.join(self.directory, statement_node.attrib['path']),
                                         statement_node.attrib['charset'], statement_node.attrib['language'])

  def save_judging_node(self, judging_node):
    if judging_node is not None:
      any_testset = judging_node.find('testset')
      time_limit = int(any_testset.find('time-limit').text)
      memory_limit = int(any_testset.find('memory-limit').text) // 2 ** 20
      self.update_info(time_limit, memory_limit, None)

  def save_testset(self, testset_node):
    input_pattern = testset_node.find('input-path-pattern').text
    answer_pattern = testset_node.find('answer-path-pattern').text

    test_id = 0
    self.revision.cases.clear()
    group_dict = dict()
    for test_node in testset_node.find('tests').findall('test'):
      test_id += 1
      with open(os.path.join(self.directory, input_pattern % test_id), 'rb') as test_input:
        input_text = test_input.read().replace(b"\r\n", b"\n")  # process CRLF
      with open(os.path.join(self.directory, answer_pattern % test_id), 'rb') as test_answer:
        answer_text = test_answer.read().replace(b"\r\n", b"\n")  # replace \r\n
      is_sample = 'sample' in test_node.attrib and test_node.attrib["sample"] == "true"
      points = int(float(test_node.attrib.get("points", 1)))
      group_name = test_node.attrib.get("group", "")
      if not group_name:
        group_number = 1
      else:
        if group_name not in group_dict:
          nxt = len(group_dict)
          group_dict[group_name] = nxt + 1
        group_number = group_dict[group_name]
      method = test_node.attrib.get("method", "")
      case = Case.objects.create(in_samples=is_sample,
                                 points=points,
                                 description=method,
                                 case_number=test_id,
                                 group=group_number,
                                 create_time=datetime.now())
      case.input_file.save("in", ContentFile(input_text), save=False)
      case.output_file.save("out", ContentFile(answer_text), save=False)
      case.save_fingerprint(self.revision.problem_id)
      case.save()
      self.revision.cases.add(case)

    groups_node = testset_node.find("groups")
    if groups_node is not None:
      self.revision.enable_group = True
      self.revision.group_count = len(group_dict)
      points = [10] * self.revision.group_count
      dependencies = []
      for group in groups_node.findall("group"):
        group_name = group.attrib["name"]
        group_id = group_dict[group_name]
        points[group_id - 1] = int(float(group.attrib["points"]))
        dependencies_node = group.find("dependencies")
        if dependencies_node is not None:
          for dependency_node in dependencies_node.findall("dependency"):
            dependency_group_id = group_dict[dependency_node.attrib["group"]]
            dependencies.append((group_id, dependency_group_id))
      self.revision.group_points = ",".join(map(str, points))
      self.revision.group_dependencies = ";".join(map(lambda s: "%s,%s" % (s[0], s[1]), dependencies))
    else:
      self.revision.enable_group = False

  def build(self):
    with transaction.atomic():
      path_to_problemxml = os.path.join(self.directory, 'problem.xml')
      if os.path.isfile(path_to_problemxml):
        problem_node = ElementTree.parse(path_to_problemxml)
      else:
        raise RuntimeError("problem.xml not found or couldn't be opened")

      statements_node = problem_node.find('statements')
      if statements_node is not None:
        for statement_node in statements_node.findall('statement'):
          if self.save_statement(statement_node):
            break

      self.save_judging_node(problem_node.find("judging"))

      assets_node = problem_node.find('assets')
      for checker_node in assets_node.findall('checker'):
        source_node = checker_node.find('source')
        self.set_utility_file(source_node.attrib['path'], source_node.attrib['type'], 'checker')
      interactor_node = assets_node.find('interactor')
      if interactor_node is not None:
        source_node = interactor_node.find('source')
        self.set_utility_file(source_node.attrib['path'], source_node.attrib['type'], 'interactor')
      for testset_node in problem_node.find('judging').findall('testset'):
        testset_name = testset_node.attrib['name']
        if testset_name != "tests":
          # EOJ doesn't support multiple testset
          continue
        self.save_testset(testset_node)
        break

      self.revision.save()


class PackageImportView(ProblemRevisionMixin, FormView):
  class ImportForm(forms.Form):
    package_file = forms.FileField(required=True)

  template_name = "polygon/problem2/package.jinja2"
  form_class = ImportForm

  def form_valid(self, form):
    file = form.cleaned_data["package_file"]
    tmp_directory = '/tmp/' + random_string()
    with zipfile.ZipFile(file) as myZip:
      myZip.extractall(path=tmp_directory)
    try:
      CodeforcesPackageAdapter(tmp_directory, self.revision).build()
    except:
      form.add_error(None, traceback.format_exc())
      shutil.rmtree(tmp_directory, ignore_errors=True)
      return super().form_invalid(form)
    shutil.rmtree(tmp_directory)
    return super().form_valid(form)

  def get_success_url(self):
    return reverse("polygon:revision_update", kwargs={"pk": self.problem.id, "rpk": self.revision.id})
