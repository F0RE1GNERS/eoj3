import re
import zipfile
from datetime import datetime

import io

import chardet
from django.core.files.base import ContentFile, File
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView
from os import path

from polygon.models import Case
from polygon.problem.forms import CaseUpdateForm, CaseCreateForm, CaseUpdateInfoForm
from polygon.problem.views.base import ProblemRevisionMixin
from utils import random_string
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


REFORMAT = CaseManagementTools.reformat


class CaseList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem/case/list.jinja2'
    context_object_name = 'case_list'

    def get_queryset(self):
        qs = self.revision.cases.all()
        for case in qs:
            case.comments = []
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


class CaseCreateView(ProblemRevisionMixin, FormView):
    form_class = CaseCreateForm
    template_name = 'polygon/problem/simple_form.jinja2'

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
                    case.input_file.save("in", File(ins))
                    case.output_file.save("out", File(ous))
                    case.save_fingerprint(self.problem.id)
                    cases.append(case)
            # TODO: catch exception

        # process case numbers
        remove_list = []
        if case_number_start <= 0:
            # auto fill the empty indices
            idx = 1
            exist = set(self.revision.cases.all().values_list("case_number", flat=True))
            for case in cases:
                while idx in exist:
                    idx += 1
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

        return super().form_valid(form)


class CaseUpdateFileView(ProblemRevisionMixin, FormView):
    form_class = CaseUpdateForm
    template_name = 'polygon/problem/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self):
        try:
            return self.revision.cases.get(pk=self.kwargs['cpk'])
        except Case.DoesNotExist:
            raise Http404("No cases found matching the query")

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
        return super().form_valid(form)


class CaseUpdateInfoView(ProblemRevisionMixin, UpdateView):
    form_class = CaseUpdateInfoForm
    template_name = 'polygon/problem/simple_form.jinja2'

    def get_success_url(self):
        return reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id})

    def get_object(self, queryset=None):
        try:
            return self.revision.cases.get(pk=self.kwargs['cpk'])
        except Case.DoesNotExist:
            raise Http404("No cases found matching the query")

    def form_valid(self, form):
        with transaction.atomic():
            self.revision.cases.remove(self.object)
            form.instance.parent_id = form.instance.pk
            form.instance.pk = None
            self.object = form.save()
            self.revision.cases.add(self.object)
        return super().form_valid(form)


class CaseDeleteView(ProblemRevisionMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            object = self.revision.cases.get(pk=kwargs['cpk'])
            self.revision.cases.remove(object)
            return redirect(reverse('polygon:revision_case', kwargs={'pk': self.problem.id, 'rpk': self.revision.id}))
        except Case.DoesNotExist:
            raise Http404("No cases found matching the query")
