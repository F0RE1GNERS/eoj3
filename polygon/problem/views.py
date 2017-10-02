import json
import re
import traceback
from os import path, remove

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import HttpResponseServerError
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, UpdateView, TemplateView
from django.views.generic.base import ContextMixin

from account.models import User
from account.permissions import is_admin_or_root
from polygon.base_views import PolygonBaseMixin
from polygon.models import EditSession
from polygon.problem.case import well_form_text
from polygon.problem.forms import ProblemEditForm
from polygon.problem.session import init_session, pull_session, load_config, save_program_file, delete_program_file, \
    read_program_file, toggle_program_file_use, save_case, read_case, \
    process_uploaded_case, reform_case, validate_case, get_case_output, check_case, delete_case, \
    get_test_file_path, generate_input, stress, update_multiple_case_config, push_session
from polygon.problem.utils import sort_out_directory
from polygon.rejudge import rejudge_all_submission_on_problem
from problem.models import Problem, SpecialProgram
from problem.views import StatusList
from submission.models import Submission
from utils import random_string
from utils.download import respond_as_attachment
from utils.language import LANG_CHOICE
from utils.permission import is_problem_manager
from utils.upload import save_uploaded_file_to


class ProblemList(PolygonBaseMixin, ListView):
    template_name = 'polygon/problem/list.jinja2'
    context_object_name = 'problem_list'
    paginate_by = 250

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            return Problem.objects.all()
        else:
            return self.request.user.managing_problems.all()


class ProblemCreate(PolygonBaseMixin, View):

    def post(self, request, *args, **kwargs):
        problem = Problem.objects.create()
        problem.title = 'Problem #%d' % problem.id
        problem.alias = 'p%d' % problem.id
        problem.checker = SpecialProgram.objects.filter(filename='fcmp.cpp', builtin=True).first().fingerprint
        problem.save(update_fields=['title', 'alias', 'checker'])
        problem.managers.add(request.user)
        return HttpResponse()


class PolygonProblemMixin(ContextMixin, PolygonBaseMixin):
    raise_exception = True

    def init_session_during_dispatch(self):
        pass

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
        self.init_session_during_dispatch()
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_problem_manager(self.request.user, self.problem):
            return False
        return super(PolygonProblemMixin, self).test_func()

    def get_context_data(self, **kwargs):
        data = super(PolygonProblemMixin, self).get_context_data(**kwargs)
        data['problem'] = self.problem
        data['lang_choices'] = LANG_CHOICE
        data['builtin_program_choices'] = SpecialProgram.objects.filter(builtin=True).all()
        return data


class BaseSessionMixin(PolygonProblemMixin):

    def init_session_during_dispatch(self):
        if not (self.get_test_func())():
            # Manually check permission to make sure there is no redundant session created
            # Call super before update session does not work
            return self.handle_no_permission()
        try:
            self.session = self.problem.editsession_set.get(user=self.request.user)
        except EditSession.DoesNotExist:
            self.session = init_session(self.problem, self.request.user)
        self.config = load_config(self.session)

    def get_context_data(self, **kwargs):
        data = super(BaseSessionMixin, self).get_context_data(**kwargs)
        data['session'], data['config'] = self.session, self.config
        return data


class SessionPostMixin(BaseSessionMixin):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            messages.add_message(request, messages.ERROR, "%s: %s" % (e.__class__.__name__, str(e)))
            return HttpResponse()


class ProblemPreview(PolygonProblemMixin, TemplateView):
    template_name = 'polygon/problem/preview.jinja2'


class ProblemAccessManage(PolygonProblemMixin, View):
    def post(self, request, pk):
        upload_permission_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        for record in self.problem.managers.all():
            if record.id in upload_permission_set:
                upload_permission_set.remove(record.id)
            else:
                record.delete()
        for key in upload_permission_set:
            self.problem.managers.add(User.objects.get(pk=key))
        return redirect(reverse('polygon:problem_edit', kwargs={'pk': str(pk)}))


class ProblemEdit(PolygonProblemMixin, UpdateView):

    template_name = 'polygon/problem/edit.jinja2'
    form_class = ProblemEditForm
    queryset = Problem.objects.all()

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.tags = form.cleaned_data['tags']
        instance.save()
        return redirect(self.request.path)

    def get_object(self, queryset=None):
        return self.problem

    def get_context_data(self, **kwargs):
        data = super(ProblemEdit, self).get_context_data(**kwargs)
        data['admin_list'] = self.problem.managers.all()
        return data

    def get_success_url(self):
        return self.request.path


class ProblemStatus(PolygonProblemMixin, StatusList):
    template_name = 'polygon/problem/status.jinja2'

    def get_selected_from(self):
        return Submission.objects.filter(problem_id=self.problem.id)


class ProblemRejudge(PolygonProblemMixin, View):

    def post(self, request, *args, **kwargs):
        rejudge_all_submission_on_problem(self.problem)
        return redirect(reverse('polygon:problem_status', kwargs={'pk': self.problem.id}))


class ProblemPull(PolygonProblemMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            session = EditSession.objects.get(problem=self.problem, user=request.user)
            pull_session(session)
        except EditSession.DoesNotExist:
            init_session(self.problem, request.user)
        return HttpResponse()


class ProblemPush(SessionPostMixin, View):
    def post(self, request, *args, **kwargs):
        push_session(self.session)
        return HttpResponse()


class ProblemStaticFileList(PolygonProblemMixin, ListView):
    template_name = 'polygon/problem/files.jinja2'
    context_object_name = 'file_list'

    def get_queryset(self):
        r = sort_out_directory(path.join(settings.UPLOAD_DIR, str(self.problem.pk)))
        for dat in r:
            dat['url'] = '/upload/%d/%s' % (self.problem.id, dat['filename'])
            if re.search(r'(gif|jpg|jpeg|tiff|png)$', dat['filename'], re.IGNORECASE):
                dat['type'] = 'image'
            else:
                dat['type'] = 'regular'
        return r


class ProblemUploadStaticFile(PolygonProblemMixin, View):
    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist("files[]")
        for file in files:
            save_uploaded_file_to(file, path.join(settings.UPLOAD_DIR, str(self.problem.pk)),
                                  filename=path.splitext(file.name)[0] + '.' + random_string(16),
                                  keep_extension=True)
        return HttpResponse()


class ProblemDeleteRegularFile(PolygonProblemMixin, View):
    def post(self, request, *args, **kwargs):
        filename = request.POST['filename']
        try:
            upload_base_dir = path.join(settings.UPLOAD_DIR, str(self.problem.pk))
            real_path = path.abspath(path.join(upload_base_dir, filename))
            if path.commonpath([real_path, upload_base_dir]) != upload_base_dir:
                raise PermissionDenied
            remove(real_path)
        except OSError:
            return HttpResponseServerError()
        return HttpResponse()


class SessionProgramList(BaseSessionMixin, TemplateView):
    template_name = 'polygon/problem/program.jinja2'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["program_list"] = program_list = []
        for filename, val in self.config["program"].items():
            program_list.append(dict(filename=filename))
            program_list[-1].update(val)
            program_list[-1]["lang_display"] = dict(LANG_CHOICE)[program_list[-1]["lang"]]
            program_list[-1]["code"] = read_program_file(self.session, filename)
            for sp_type in ['checker', 'validator', 'generator', 'interactor', 'model']:
                if self.config.get(sp_type) == filename:
                    program_list[-1].update(used=True)
        return data


class SessionCreateProgram(SessionPostMixin, View):
    def post(self, request, *args, **kwargs):
        filename, type, lang, code = request.POST['filename'], request.POST['type'], \
                                     request.POST['lang'], request.POST['code']
        save_program_file(self.session, filename, type, lang, code)
        return HttpResponse()


class SessionImportProgram(SessionPostMixin, View):
    def post(self, request, *args, **kwargs):
        type = request.POST['type']
        sp = SpecialProgram.objects.get(builtin=True, filename=type)
        save_program_file(self.session, sp.filename, sp.category, sp.lang, sp.code)
        return HttpResponse()


class SessionUpdateProgram(SessionPostMixin, View):
    def post(self, request, *args, **kwargs):
        raw_filename = request.POST['rawfilename']
        filename, type, lang, code = request.POST['filename'], request.POST['type'], \
                                     request.POST['lang'], request.POST['code']
        save_program_file(self.session, filename, type, lang, code, raw_filename)
        return HttpResponse()


class SessionDeleteProgram(SessionPostMixin, View):
    def post(self, request, *args, **kwargs):
        filename = request.POST['filename']
        delete_program_file(self.session, filename)
        return HttpResponse()


class SessionProgramUsedToggle(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        filename = request.POST['filename']
        toggle_program_file_use(self.session, filename)
        return HttpResponse()


class SessionCaseList(BaseSessionMixin, TemplateView):
    template_name = 'polygon/problem/case.jinja2'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['program_list'] = program_list = []
        for filename, val in self.config["program"].items():
            program_list.append(dict(filename=filename, type=val['type']))
        return data


class SessionCaseDataAPI(BaseSessionMixin, View):
    def get_case_config(self, case_id):
        case_dict = self.config['case'][case_id]
        case_dict.update(fingerprint=case_id)
        case_dict.update(read_case(self.session, case_id))
        return case_dict

    def get(self, request, *args, **kwargs):
        case_id = request.GET.get('id')
        if case_id is not None:
            return JsonResponse(self.get_case_config(case_id))
        else:
            for fingerprint, val in self.config['case'].items():
                val.update(fingerprint=fingerprint)
                val.setdefault('selected', False)
            case_list = sorted(self.config['case'].values(), key=lambda x: (not bool(x['order']), x['order']))
            return JsonResponse({'caseList': case_list})

    def post(self, request, *args, **kwargs):
        """
        A example of request.POST:
        <QueryDict: {'outputText': ['5\r\n'], 'sample': ['on'], 'point': ['10'], 'pretest': ['on'], 'outputType':
        ['editor'], 'inputText': ['2 3\r\n'], 'reform': ['on'], 'inputFile': [''], 'inputType': ['editor'], 'outputFile': ['']}>
        """
        case_id = request.GET['id']
        case_config = self.get_case_config(case_id)

        if not case_config['input']['nan'] and request.POST['inputType'] == 'editor':
            input = request.POST['inputText']
        elif request.FILES.get('inputFile') and request.POST['inputType'] == 'upload':
            input = request.FILES['inputFile'].read().decode()
            # TODO: universal decoding
        else:
            input = read_case(self.session, case_id, type='in')

        if not case_config['output']['nan'] and request.POST['outputType'] == 'editor':
            output = request.POST['outputText']
        elif request.FILES.get('outputFile') and request.POST['outputType'] == 'upload':
            output = request.FILES['outputFile'].read().decode()
        else:
            output = read_case(self.session, case_id, type='out')

        well_form = request.POST.get('reform') == 'on'
        if well_form:
            input, output = well_form_text(input), well_form_text(output)
        save_case(self.session, input.encode(), output.encode(), raw_fingerprint=case_id,
                  sample=request.POST.get('sample') == 'on', pretest=request.POST.get('pretest') == 'on',
                  point=int(request.POST['point']), well_form=well_form)
        return HttpResponse()


class SessionCreateCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        if request.POST['type'] == 'manual':
            input = request.POST['input']
            output = request.POST['output']
            well_form = request.POST.get("wellForm") == "on"
            if well_form:
                input, output = well_form_text(input), well_form_text(output)
            if not input:
                raise ValueError('Input file cannot be empty')
            save_case(self.session, input.encode(), output.encode(), well_form=well_form)
        elif request.POST['type'] == 'upload':
            file = request.FILES['file']
            file_directory = '/tmp'
            file_path = save_uploaded_file_to(file, file_directory, filename=random_string(), keep_extension=True)
            process_uploaded_case(self.session, file_path)
            remove(file_path)
        elif request.POST['type'] == 'generate':
            generator = request.POST['generator']
            raw_param = request.POST['param']
            generate_input('Generate cases', self.session, generator, raw_param)
        elif request.POST['type'] == 'stress':
            generator = request.POST['generator']
            raw_param = request.POST['param']
            submission = request.POST['submission']
            time = int(request.POST['time']) * 60
            if time < 60 or time > 300:
                raise ValueError('Time not in range')
            stress('Stress test', self.session, generator, submission, raw_param, time)
        return HttpResponse()


class SessionSaveCaseChanges(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case_list = json.loads(request.POST['case'])
        print(case_list)
        idx = 1
        for k in case_list:
            if k.pop('used', False):
                k['order'] = idx
                idx += 1
            else:
                k['order'] = 0
        update_multiple_case_config(self.session, {k.pop('fingerprint'): k for k in case_list})
        return HttpResponse()


class SessionPreviewCase(BaseSessionMixin, View):
    def get(self, request, *args, **kwargs):
        fingerprint = request.GET['case']
        type = request.GET['type']
        return HttpResponse(read_case(self.session, fingerprint, type), content_type='text/plain')


class SessionReformCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case = request.POST['id'].split(',')
        inputOnly = request.POST.get('inputOnly') == 'on'
        for c in case:
            reform_case(self.session, c, only_input=inputOnly)
        return HttpResponse()


class SessionValidateCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case = request.POST['id'].split(',')
        validator = request.POST['program']
        validate_case("Validate", self.session, validator, case)
        return HttpResponse()


class SessionOutputCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case = request.POST['id'].split(',')
        model = request.POST['program']
        get_case_output("Output", self.session, model, case)
        return HttpResponse()


class SessionDeleteCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case = request.POST['id']
        for c in case.split(','):
            delete_case(self.session, c)
        return HttpResponse()


class SessionCheckCase(BaseSessionMixin, View):
    def post(self, request, *args, **kwargs):
        case = request.POST['id'].split(',')
        submission = request.POST['program']
        checker = request.POST['checker']
        check_case("Check", self.session, submission, checker, case)
        return HttpResponse()


class SessionDownloadCase(BaseSessionMixin, View):
    def get(self, request, sid):
        case = request.GET['fingerprint']
        input, _ = get_test_file_path(self.session, case)
        return respond_as_attachment(request, input, case + '.in')
