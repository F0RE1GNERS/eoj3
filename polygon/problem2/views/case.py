import json
import re
import zipfile
from datetime import datetime

import io

import chardet
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile, File
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from os import path

from django_q.tasks import async

from polygon.models import Case, Program, Task
from polygon.problem2.forms import CaseUpdateForm, CaseCreateForm, CaseUpdateInfoForm
from polygon.problem2.runner import Runner
from polygon.problem2.runner.exception import CompileError
from polygon.problem2.views.base import ProblemRevisionMixin
from utils import random_string
from utils.download import respond_generate_file
from utils.file_preview import sort_data_list_from_directory


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
        else: return txt

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
        remove_list = []
        add_list = []
        with transaction.atomic():
            for idx, case in enumerate(case_set, start=1):
                if idx != case.case_number:
                    remove_list.append(Case(pk=case.pk))
                    case.case_number = idx
                    case.pk = None
                    case.save()
                    add_list.append(case)
            revision.cases.add(*add_list)
            revision.cases.remove(*remove_list)

    @staticmethod
    def generate_cases(revision, commands):
        """
        report: [
            {
                success: True / False
                error: ...
                case_number: 1
                detail: ...
            }, { ... }, ...
        ]
        """
        generators = {}
        current_task = Task.objects.create(revision=revision, abstract="GENERATE CASES")
        report = []
        for command_string in commands:
            ret = {"command": command_string}
            command = command_string.split()
            program_name, program_args = command[0], command[1:]
            try:
                if program_name not in generators:
                    program = revision.programs.get(name=program_name, tag="generator")
                    generators[program_name] = Runner(program)
                elif isinstance(generators[program_name], CompileError):
                    raise generators[program_name]
                runner = generators[program_name]
                if revision.cases.all().count():
                    case_number = revision.cases.all().aggregate(Max("case_number"))["case_number__max"] + 1
                else: case_number = 1
                new_case = Case(create_time=datetime.now(),
                                description="Gen \"%s\"" % command_string,
                                case_number=case_number)
                new_case.input_file.save("in", ContentFile(b""), save=False)
                new_case.output_file.save("out", ContentFile(b""), save=False)
                running_result = runner.run(args=program_args, stdout=new_case.input_file.path,
                                            max_time=revision.time_limit * 5 / 1000,
                                            max_memory=revision.memory_limit * 3)
                CaseManagementTools.reformat_file(new_case.input_file.path, revision.well_form_policy)
                new_case.save_fingerprint(revision.problem_id)
                ret["case_number"] = case_number
                with transaction.atomic():
                    new_case.save()
                    revision.cases.add(new_case)
                    ret.update(case_number=case_number,
                               success=running_result["verdict"] == "OK",
                               detail=running_result,
                               generated=new_case.input_preview)
            except (Program.MultipleObjectsReturned, Program.DoesNotExist):
                ret.update(success=False,
                           error="There should be exactly one program tagged 'generator' that fits the command.")
            except CompileError as e:
                generators[program_name] = e
                ret.update(success=False, error=e.error)
            report.append(ret)
            current_task.status = -2
            current_task.report = json.dumps(report)
            current_task.save()
        current_task.status = 0 if all(map(lambda r: r["success"], report)) else -1

    @staticmethod
    def run_case_output(revision, case_set, solution):
        """
        report: similar to generating cases, [{ }, { }, ... { }]
        """
        current_task = Task.objects.create(revision=revision, abstract="RUN OUTPUT, %d cases" % len(case_set))
        try:
            runner = Runner(solution)
            result = []
            failed = False
            for case in case_set:
                if case.output_lock: continue  # output content protected
                case.output_file.save("out", ContentFile(b''), save=False)
                case.parent_id = case.pk
                case.pk = None
                run_result = runner.run(stdin=case.input_file.path, stdout=case.output_file.path,
                                        max_time=revision.time_limit * 3 / 1000,
                                        max_memory=revision.memory_limit * 2)
                CaseManagementTools.reformat_file(case.output_file.path, revision.well_form_policy)
                case.save_fingerprint(revision.problem_id)
                with transaction.atomic():
                    case.save()
                    revision.cases.remove(Case(pk=case.parent_id))
                    revision.cases.add(case)
                    result.append({
                        "case_number": case.case_number,
                        "success": run_result["verdict"] == "OK",
                        "detail": run_result
                    })
                    if run_result["verdict"] != "OK":
                        failed = True
                    current_task.status = -2
                    current_task.report = json.dumps(result)
                    current_task.save()
            current_task.status = -1 if failed else 0
        except CompileError as e:
            current_task.report = json.dumps([{"success": False, "error": e.error}])
            current_task.status = -1
        current_task.save()

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

    @staticmethod
    def obtain_defaultspj():
        try:
            import requests
            code = requests.get("https://raw.githubusercontent.com/ultmaster/ejudge/v2.1/lib/defaultspj.cpp").text
            program = Program(name="defaultspj", lang="cpp", code=code, tag="checker")
            program.save_fingerprint()
            return program
        except:
            raise ValueError("Default checker cannot be obtained. Check network connections.")

    @staticmethod
    def check_case(revision, case_set, solution_set, checker):
        """
        response: {
            "success": True / False,
            "error": ...,
            "tasks": [
                {
                    "verdict": "OK",
                    "solution": 23,
                    "case_number": 45,
                    "time": 15,
                    "memory": 30,
                },
                ...
            ],
            "summary": {
                solution_number: {
                    time, max_time, memory, points
                }
            }
        }
        """
        current_task = Task.objects.create(revision=revision,
                                           abstract="CHECK, %d cases, %d solutions" % (
                                               len(case_set), len(solution_set)))
        packed_result = {"success": True, "tasks": [], "summary": {}}
        try:
            solution_runners = [(solution, Runner(solution)) for solution in solution_set]
            if checker is None:
                checker = CaseManagementTools.obtain_defaultspj()
            checker_runner = Runner(checker)
            checker_result_path = path.join(checker_runner.workspace, "result")
            task_result = packed_result["tasks"]
            verdict_for_each_solution = {solution.id: set() for solution in solution_set}
            for case in case_set:
                for solution, runner in solution_runners:
                    output_path = path.join(runner.workspace, "out")
                    err_path = path.join(runner.workspace, "err")
                    result = {"solution": solution.id, "case_number": case.case_number, "case_id": case.id}
                    running_result = runner.run(stdin=case.input_file.path, stdout=output_path,
                                                max_time=revision.time_limit / 1000,
                                                max_memory=revision.memory_limit)
                    result.update(running_result)
                    result.update(input=CaseManagementTools.read_abstract(case.input_file.path),
                                  answer=CaseManagementTools.read_abstract(case.output_file.path),
                                  output=CaseManagementTools.read_abstract(output_path),
                                  stderr=CaseManagementTools.read_abstract(err_path))

                    if result["verdict"] == "OK":
                        # run checker
                        checking_result = checker_runner.run(
                            args=[case.input_file.path, output_path, case.output_file.path],
                            stdout=checker_result_path,
                            max_time=revision.time_limit / 1000 * 3,
                            max_memory=revision.memory_limit)
                        result.update(checker_comment=CaseManagementTools.read_abstract(checker_result_path),
                                      checker_exit_code=checking_result["exit_code"])
                        if checking_result["verdict"] != "OK":
                            result.update(verdict="WRONG_ANSWER")

                    if result["verdict"] == "OK":
                        result.update(points=case.points)
                    else: result.update(points=0)
                    result.update(total_points=case.points)

                    verdict_for_each_solution[solution.id].add(result["verdict"])
                    task_result.append(result)
            for solution in solution_set:
                got_verdicts = verdict_for_each_solution[solution.id]
                if solution.tag in ('solution_main', 'solution_correct') and got_verdicts != {"OK"}:
                    packed_result.update(success=False,
                                         error="'%s' claims to be correct, but got rejected in tests" % solution.name)
                if solution.tag == 'solution_tle_or_ok' and got_verdicts != {"TIME_LIMIT", "OK"}:
                    packed_result.update(success=False, error="'%s' claims to be tle_or_ok, but got %s" % (
                    solution.name, str(got_verdicts)))
                if solution.tag == 'solution_wa' and 'WRONG_ANSWER' not in got_verdicts:
                    packed_result.update(success=False, error="'%s' claims to be WA, but never got WA" % solution.name)
                if solution.tag == 'solution_incorrect' and got_verdicts == {"OK"}:
                    packed_result.update(success=False,
                                         error="'%s' claims to be incorrect, but is actually correct" % solution.name)
                if solution.tag == 'solution_fail' and "RUNTIME_ERROR" not in got_verdicts:
                    packed_result.update(success=False, error="'%s' claims to fail, but didn't fail" % solution.name)
                solution_based_result = list(filter(lambda x: x["solution"] == solution.id, task_result))
                solution_time_summary = list(map(lambda x: x["time"], solution_based_result)) + [0]
                packed_result["summary"][solution.id] = {
                    "time": max(solution_time_summary),
                    "sum_time": sum(solution_time_summary),
                    "memory": max(list(map(lambda x: x["memory"], solution_based_result)) + [0]),
                    "points": sum(list(map(lambda x: x["points"], solution_based_result)) + [0]) /
                              max(sum(list(map(lambda x: x["total_points"], solution_based_result)) + [0]), 1) * 100
                }
        except CompileError as e:
            packed_result.update(success=False, error=e.error)
        except ValueError as e:
            packed_result.update(success=True, error=e.args[0])
        current_task.status = 0 if packed_result["success"] else -1
        current_task.report = json.dumps(packed_result)
        current_task.save()


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


class CaseList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem2/case/list.jinja2'
    context_object_name = 'case_list'

    def get_queryset(self):
        qs = self.revision.cases.all().order_by("case_number")
        for case in qs:
            case.comments = []
            if case.description:
                case.comments.append(case.description)
            if case.in_samples:
                case.comments.append("Sample")
            if case.in_pretests:
                case.comments.append("Pretest")
            if case.output_lock:
                case.comments.append("Output locked")
            if not case.activated:
                case.comments.append("Excluded in tests")
            case.comments.append("Worth %d pts." % case.points)
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["disable_grid"] = True
        return data


class CaseCreateView(ProblemRevisionMixin, FormView):
    form_class = CaseCreateForm
    template_name = 'polygon/problem2/case/create.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def form_valid(self, form):
        global_create_time = datetime.now()
        option = form.cleaned_data["option"]
        case_number_start = form.cleaned_data["case_number"]
        cases = []

        if option in ("single", "text"):
            if option == "single":
                input_binary = REFORMAT(form.cleaned_data["input_file"].read(), self.revision.well_form_policy)
                output_binary = REFORMAT(form.cleaned_data["output_file"].read(), self.revision.well_form_policy)
                description = "File \"%s\" and \"%s\"" % (
                    form.cleaned_data["input_file"].name, form.cleaned_data["output_file"].name)
            else:
                input_binary = REFORMAT(form.cleaned_data["input_text"].encode(), self.revision.well_form_policy)
                output_binary = REFORMAT(form.cleaned_data["output_text"].encode(), self.revision.well_form_policy)
                description = "Typed-in case"
            case = Case(create_time=global_create_time,
                        in_samples=form.cleaned_data["in_samples"],
                        output_lock=form.cleaned_data["output_lock"],
                        description=description,
                        activated=form.cleaned_data["activated"])
            case.input_file.save("in", ContentFile(input_binary), save=False)
            case.output_file.save("out", ContentFile(output_binary), save=False)
            case.save_fingerprint(self.problem.id)
            cases.append(case)

        elif option == "batch":
            tmp_directory = '/tmp/' + random_string()
            with zipfile.ZipFile(form.cleaned_data["batch_file"]) as myZip:
                myZip.extractall(path=tmp_directory)
            for inf, ouf in sort_data_list_from_directory(tmp_directory):
                with open(path.join(tmp_directory, inf), 'rb') as ins, open(path.join(tmp_directory, ouf),
                                                                            'rb') as ous:
                    case = Case(create_time=global_create_time,
                                description="From \"%s\": (%s, %s)" % (form.cleaned_data["batch_file"].name,
                                                                       inf, ouf))
                    case.input_file.save("in", File(ins), save=False)
                    case.output_file.save("out", File(ous), save=False)
                    case.save_fingerprint(self.problem.id)
                    cases.append(case)
            # TODO: catch exception
        elif option == "batch_input":
            pass
        elif option == "gen":
            commands = list(map(lambda x: " ".join(x.split()),
                                filter(lambda x: x, form.cleaned_data["gen_command"].split("\n"))))
            async(CaseManagementTools.generate_cases, self.revision, commands)

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

        messages.success(self.request, "%d case(s) has been added." % len(cases))

        return redirect(self.get_success_url())


class CaseUpdateFileView(RevisionCaseMixin, FormView):
    form_class = CaseUpdateForm
    template_name = 'polygon/problem2/case/update.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self):
        return self.case

    def form_valid(self, form):
        with transaction.atomic():
            object = self.get_object()
            self.revision.cases.remove(object)
            if form.cleaned_data["option"] == "file":
                input_binary = REFORMAT(form.cleaned_data["input_file"].read(), self.revision.well_form_policy)
                output_binary = REFORMAT(form.cleaned_data["output_file"].read(), self.revision.well_form_policy)
            else:
                input_binary = REFORMAT(form.cleaned_data["input_text"].encode(), self.revision.well_form_policy)
                output_binary = REFORMAT(form.cleaned_data["output_text"].encode(), self.revision.well_form_policy)
            object.parent_id = object.pk
            object.pk = None
            object.input_file.save("in", ContentFile(input_binary), save=False)
            object.output_file.save("out", ContentFile(output_binary), save=False)
            object.save_fingerprint(self.problem.id)
            object.save()
            self.revision.cases.add(object)
        return redirect(self.get_success_url())


class CaseUpdateInfoView(RevisionCaseMixin, UpdateView):
    form_class = CaseUpdateInfoForm
    template_name = 'polygon/problem2/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        return self.case

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.cases.remove(self.object)
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            self.revision.cases.add(self.object)
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
        else: p = self.case.output_file.read()
        return HttpResponse(p, content_type="text/plain; charset=utf-8")


class CaseNaturalizeOrderView(ProblemRevisionMixin, View):
    def post(self, request, *args, **kwargs):
        qs = self.revision.cases.all().order_by("case_number")
        NATURALIZE_ORDER(self.revision, qs)
        return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CaseMoveOrderView(RevisionMultipleCasesMixin, View):
    def post(self, request, *args, **kwargs):
        after = int(request.POST.get("answer", 0))
        other_case_set = self.revision.cases.exclude(pk__in=self.pk_set).order_by("case_number")
        insert_pos = 0
        while insert_pos < len(other_case_set) and other_case_set[insert_pos].case_number <= after:
            insert_pos += 1
        ret = other_case_set[:insert_pos] + list(self.case_set) + other_case_set[insert_pos:]
        NATURALIZE_ORDER(self.revision, ret)
        return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CaseDeleteSelectedView(RevisionMultipleCasesMixin, View):
    def post(self, request, *args, **kwargs):
        self.revision.cases.remove(*list(self.case_set))
        NATURALIZE_ORDER(self.revision, self.revision.cases.all().order_by("case_number"))
        return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CaseRunSelectedOutput(RevisionMultipleCasesMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            solution = self.revision.programs.get(tag="solution_main")
            async(CaseManagementTools.run_case_output, self.revision, self.case_set, solution)
        except (Program.MultipleObjectsReturned, Program.DoesNotExist):
            messages.error(request, "There should be exactly one main correct solution!")
        return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CaseCheckView(ProblemRevisionMixin, TemplateView):
    template_name = 'polygon/problem2/case/check.jinja2'
    raise_exception = True

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'gather' not in self.request.GET:
            raise PermissionDenied
        data['select_cases'] = self.request.GET['gather']
        data['program_list'] = self.revision.programs.filter(tag__contains='solution').all()
        return data

    def post(self, request, *args, **kwargs):
        case_pk_set = set(filter(lambda x: x, request.POST["cases"].split(",")))
        if not case_pk_set:
            messages.error(request, "Invalid selected cases")
            return redirect(request.path)
        case_set = self.revision.cases.filter(pk__in=case_pk_set).order_by("case_number")
        program_pk_set = set()
        for p, switch in request.POST.items():
            if switch == 'on' and p.isdigit():
                program_pk_set.add(int(p))
        if not program_pk_set:
            messages.error(request, "Please select at least one solution.")
        program_set = self.revision.programs.filter(pk__in=program_pk_set)
        if len(case_pk_set) != len(case_set) or len(program_pk_set) != len(program_set):
            messages.error(request, "Invalid selected cases or solutions.")
        async(CaseManagementTools.check_case, self.revision, case_set, program_set, self.revision.active_checker)
        return redirect(reverse('polygon:revision_task', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))


class CasePackAsZipView(ProblemRevisionMixin, View):
    def get_redirect_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get(self, request, *args, **kwargs):
        cases = list(self.revision.cases.all().order_by("case_number"))
        if len(cases) == 0:
            messages.error(request, "There are no cases to pack.")
            return redirect(self.get_redirect_url())
        for idx, case in enumerate(cases):
            if idx > 0 and case.case_number == cases[idx - 1].case_number:
                messages.error(request, "Cases refuse to pack because there are two cases with the same case number.")
                return redirect(self.get_redirect_url())
        file_path = path.join(settings.GENERATE_DIR, random_string())
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip:
            for case in cases:
                zip.write(case.input_file.path, arcname="%d.in" % case.case_number)
                zip.write(case.output_file.path, arcname="%d.out" % case.case_number)
        return respond_generate_file(request, file_path,
                                     "PackedTestCases - %s#%d.zip" % (self.problem.alias, self.revision.revision))
