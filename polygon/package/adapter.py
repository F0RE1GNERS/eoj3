import os
import re
from xml.etree import ElementTree

from django.db import transaction

from dispatcher.models import Server, ServerProblemStatus
from polygon.models import CodeforcesPackage
from polygon.package.codeforces import get_working_directory
from problem.models import Problem, SpecialProgram, get_input_path, get_output_path
from problem.tasks import upload_problem_to_judge_server
from utils.hash import sha_hash, case_hash

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
  "python.2":"py2",
  "python.3": "python",
  "rust": "rs",
  "scala": "scala"
}


class CodeforcesPackageAdapter:
  def __init__(self, package: CodeforcesPackage, problem: Problem):
    self.package = package
    self.problem = problem
    self.directory = os.path.join(get_working_directory(self.package.dir_name), "package")

  def add_problem_option(self, name, value):
    if value is not None:
      setattr(self.problem, name, value)

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
    self.add_problem_option('interactive', interactive)
    return True

  def set_utility_file(self, path, lang, name):
    with open(os.path.join(self.directory, path), "r") as f:
      code = f.read()
    lang = LANGUAGE_ADAPTER[lang]
    fingerprint = sha_hash(sha_hash(lang) + sha_hash(code) + sha_hash(name))
    try:
      sp = SpecialProgram.objects.get(fingerprint=fingerprint)
    except:
      sp = SpecialProgram.objects.create(fingerprint=fingerprint, lang=lang, filename=name,
                                         category=name, code=code)
    setattr(self.problem, name, sp.fingerprint)

  def save_statement_from_file(self, filepath, encoding, language):
    with open(filepath, 'r', encoding=encoding) as statement_file:
      content = statement_file.read()
    self.problem.title = content[len('\\begin{problem}{'):content.find('}', len('\\begin{problem}{'))]
    content = content[content.find('\n') + 1:]
    input_format_start = content.find('\\InputFile')
    self.problem.description = content[:input_format_start]
    content = content[input_format_start:]
    content = content[content.find('\n') + 1:]
    output_format_start = content.find('\\OutputFile')
    self.problem.input = content[:output_format_start]
    content = content[output_format_start:]
    content = content[content.find('\n') + 1:]
    self.problem.output = content[:content.find('\\Example')]
    notes_start_pos = content.find('\\Note')
    if notes_start_pos >= 0:
      content = content[notes_start_pos:]
      content = content[content.find('\n') + 1:]
      self.problem.hint = content[:content.find('\\end{problem}')]
    return True

  def save_statement(self, statement_node):
    # TODO: images support
    # TODO: TeX (and others) support
    # TODO: interaction, tutorial support
    # TODO: deal with assets
    if not statement_node.attrib['type'].endswith('tex'):
      return
    return self.save_statement_from_file(os.path.join(self.directory, statement_node.attrib['path']),
                                         statement_node.attrib['charset'], statement_node.attrib['language'])

  def save_judging_node(self, judging_node):
    if judging_node is not None:
      input_file_name = judging_node.attrib['input-file']   # ignore input and output
      output_file_name = judging_node.attrib['output-file'] # read them anyway
      any_testset = judging_node.find('testset')
      time_limit = int(any_testset.find('time-limit').text)
      memory_limit = int(any_testset.find('memory-limit').text) // 2 ** 20
      self.update_info(time_limit, memory_limit, None)

  def save_testset(self, testset_node):
    input_pattern = testset_node.find('input-path-pattern').text
    answer_pattern = testset_node.find('answer-path-pattern').text

    # TODO: group support
    test_id = 0
    tests, samples = [], []
    for test_node in testset_node.find('tests').findall('test'):
      test_id += 1
      if test_node.attrib['method'] == 'manual':
        with open(os.path.join(self.directory, input_pattern % test_id), 'rb') as test_input:
          # process CRLF
          input_text = test_input.read().replace(b"\r\n", b"\n")
        with open(os.path.join(self.directory, answer_pattern % test_id), 'rb') as test_answer:
          answer_text = test_answer.read().replace(b"\r\n", b"\n")
        hash_str = case_hash(self.problem.id, input_text, answer_text)
        input_path, answer_path = get_input_path(hash_str), get_output_path(hash_str)
        with open(input_path, "wb") as test_input, open(answer_path, "wb") as test_answer:
          test_input.write(input_text)
          test_answer.write(answer_text)
        if 'sample' in test_node.attrib and test_node.attrib["sample"] == "true":
          samples.append(hash_str)
        tests.append(hash_str)
    self.problem.cases = ",".join(tests)
    self.problem.points = ",".join(["10"] * len(tests))
    self.problem.sample = ",".join(samples)

  def update(self, update_statement):
    with transaction.atomic():
      path_to_problemxml = os.path.join(self.directory, 'problem.xml')
      if os.path.isfile(path_to_problemxml):
        problem_node = ElementTree.parse(path_to_problemxml)
      else:
        raise RuntimeError("problem.xml not found or couldn't be opened")

      self.problem.alias = problem_node.getroot().attrib["short-name"]

      if update_statement:
        for statement_node in problem_node.find('statements').findall('statement'):
          if self.save_statement(statement_node):
            break

      self.save_judging_node(problem_node.find("judging"))

      files_node = problem_node.find('files')
      if files_node is not None:
        resources_node = files_node.find('resources')
        if resources_node is not None:
          # TODO: process resource
          pass
        attachments_node = files_node.find('attachments')
        if attachments_node is not None:
          # TODO: process attachments
          for attachment_node in attachments_node.findall('file'):
            pass
        executables_node = files_node.find('executables')
        if executables_node is not None:
          for executable_node in executables_node.findall('executable'):
            # TODO: process executables
            pass

      assets_node = problem_node.find('assets')
      for checker_node in assets_node.findall('checker'):
        source_node = checker_node.find('source')
        self.set_utility_file(source_node.attrib['path'], source_node.attrib['type'], 'checker')
      validators_node = assets_node.find('validators')
      if validators_node is not None:
        for validator_node in validators_node.findall('validator'):
          source_node = validator_node.find('source')
          self.set_utility_file(source_node.attrib['path'], source_node.attrib['type'], 'validator')

      for testset_node in problem_node.find('judging').findall('testset'):
        testset_name = testset_node.attrib['name']
        if testset_name != "tests":
          # EOJ doesn't support multiple testset
          continue
        self.save_testset(testset_node)
        break

      for server in Server.objects.filter(enabled=True).all():
        upload_problem_to_judge_server(self.problem, server)
        status, _ = ServerProblemStatus.objects.get_or_create(problem=self.problem, server=server)
        status.save()
      self.problem.save()
