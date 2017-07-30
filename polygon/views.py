import json
import re
from os import path, remove

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.views.generic import ListView, View, DetailView, TemplateView
from django.views.generic.base import TemplateResponseMixin, ContextMixin

from account.permissions import is_admin_or_root
from problem.models import Problem, ProblemManagement, SpecialProgram
from utils import random_string
from utils.upload import save_uploaded_file_to
from utils.language import LANG_CHOICE
from utils.download import respond_as_attachment
from .models import EditSession, Run
from .session import (
    init_session, pull_session, load_config, normal_regex_check, update_config, dump_config, load_volume,
    load_statement_file_list, create_statement_file, delete_statement_file, read_statement_file, write_statement_file,
    statement_file_exists, load_regular_file_list, load_program_file_list, program_file_exists, get_config_update_time,
    read_program_file, save_program_file, delete_program_file, save_case, get_case_metadata, reorder_case, preview_case,
    process_uploaded_case, reform_case, readjust_case_point, validate_case, get_case_output, check_case, delete_case,
    get_test_file_path
)
from .case import well_form_text


def home_view(request):
    return render(request, 'polygon/home.jinja2', context={'polygon_authorized': True})
    # TODO: polygon authorization


def register_view(request):
    template_name = 'polygon/register.jinja2'
    if request.method == 'GET':
        return render(request, template_name)
    else:
        if request.POST.get('terms') != 'on':
            return render(request, template_name, context={'register_error': 'You did\'nt accept terms of use.'})
        # TODO: or not authorized:
        request.user.polygon_enabled = True
        request.user.save(update_fields=['polygon_enabled'])
        return redirect(reverse('polygon:home'))


def response_ok(**kwargs):
    kwargs.update(status='received')
    return HttpResponse(json.dumps(kwargs))


class SessionList(ListView):
    template_name = 'polygon/session_list.jinja2'
    paginate_by = 20
    context_object_name = 'problem_manage_list'

    def get_queryset(self):
        return self.request.user.problemmanagement_set.select_related("problem").\
            all().order_by("problem__update_time").reverse()

    def get_context_data(self, **kwargs):
        data = super(SessionList, self).get_context_data(**kwargs)
        data['problems'] = problems = []
        for problem_manage in data['problem_manage_list']:
            prob = problem_manage.problem
            prob.access_type = problem_manage.get_permission_display()
            prob.sessions = prob.editsession_set.select_related("problem", "user").all()
            problems.append(prob)
        data['problemset_count'] = Problem.objects.count()
        return data


class SessionCreate(View):

    def post(self, request):
        """
        It is actually "repository create"
        named "session create" for convenience
        """
        if request.method == 'POST':
            alias = request.POST['alias']
            if not normal_regex_check(alias):
                raise ValueError
            problem = Problem.objects.create(alias=alias)
            if is_admin_or_root(request.user):
                permission = 'a'
            else:
                permission = 'w'
            ProblemManagement.objects.create(problem=problem, user=request.user, permission=permission)
            init_session(problem, request.user)
            return redirect(request.POST['next'])


class SessionPull(View):

    def post(self, request):
        problem = get_object_or_404(Problem, id=request.POST['problem'])
        # verify permission
        try:
            if ProblemManagement.objects.get(problem=problem, user=request.user).permission == 'r':
                raise PermissionDenied
        except ProblemManagement.DoesNotExist:
            raise PermissionDenied
        try:
            session = EditSession.objects.get(problem=problem, user=request.user)
            pull_session(session)
        except EditSession.DoesNotExist:
            init_session(problem, request.user)
        messages.add_message(request, messages.SUCCESS, "Synchronization succeeded!")
        return redirect(request.POST['next'])


class ProblemAccess(DetailView):

    template_name = 'polygon/problem_meta.jinja2'
    model = Problem


class RunsList(ListView):
    template_name = 'polygon/runs.jinja2'
    paginate_by = 100
    context_object_name = 'runs_list'

    def get_queryset(self):
        return Run.objects.filter(user=self.request.user).order_by("-pk").all()


class RunMessageView(View):

    def get(self, request, pk):
        try:
            run = Run.objects.get(pk=pk, user=request.user)
            return HttpResponse(run.message)
        except Run.DoesNotExist:
            return HttpResponse("")


class RunStatus(View):

    def get(self, request, pk):
        return response_ok(run_status=Run.objects.get(pk=pk, user=request.user).status)


class BaseSessionMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        try:
            self.user = request.user
            if not self.user.is_authenticated:
                raise PermissionDenied
            self.session = get_object_or_404(EditSession, pk=kwargs.get('sid'))
            self.problem = self.session.problem
            self.access = self.problem.problemmanagement_set.get(user=self.user).permission
            self.config = load_config(self.session)
        except ProblemManagement.DoesNotExist:
            raise PermissionDenied
        self.request = request
        return super(BaseSessionMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.request.method == 'POST':
            if self.access == 'r':
                return False
            if self.session.user != self.user:
                return False
        return True

    def get_context_data(self, **kwargs):
        data = super(BaseSessionMixin, self).get_context_data(**kwargs)
        data['session'], data['problem'], data['access'], data['config'] = \
            self.session, self.problem, self.access, self.config
        return data


class SessionEdit(BaseSessionMixin, TemplateView):

    template_name = 'polygon/session_edit.jinja2'

    def get_context_data(self, **kwargs):
        data = super(SessionEdit, self).get_context_data(**kwargs)
        data['lang_choices'] = LANG_CHOICE
        data['builtin_program_choices'] = SpecialProgram.objects.filter(builtin=True).all()
        return data


class SessionEditUpdateAPI(BaseSessionMixin, View):

    def get(self, request, sid):
        data = self.get_context_data(sid=sid)
        app_data = data['config']
        app_data['config_update_time'] = get_config_update_time(self.session)
        app_data['problem_id'] = self.problem.id
        app_data['case_count'] = len(list(filter(lambda x: x.get('order'), app_data['case'].values())))
        app_data['pretest_count'] = len(list(filter(lambda x: x.get('pretest'), app_data['case'].values())))
        app_data['sample_count'] = len(list(filter(lambda x: x.get('sample'), app_data['case'].values())))
        app_data['statement_file_list'] = load_statement_file_list(self.session)
        app_data['statement_identifier'] = ['description', 'input', 'output', 'hint']
        for dat in app_data['statement_file_list']:
            for identifier in app_data['statement_identifier']:
                if dat['filename'] == app_data[identifier]:
                    dat['used'] = identifier
        app_data['volume_used'], app_data['volume_all'] = load_volume(self.session)
        app_data['regular_file_list'] = load_regular_file_list(self.session)
        for dat in app_data['regular_file_list']:
            dat['url'] = '/upload/%d/%s' % (self.problem.id, dat['filename'])
            if re.search(r'(gif|jpg|jpeg|tiff|png)$', dat['filename'], re.IGNORECASE):
                dat['type'] = 'image'
            else:
                dat['type'] = 'regular'
        app_data['program_special_identifier'] = ['checker', 'validator', 'generator', 'interactor', 'model']
        app_data['program_file_list'] = load_program_file_list(self.session)
        language_choice_dict = dict(LANG_CHOICE)
        for dat in app_data['program_file_list']:
            extra_data = app_data['program'].get(dat['filename'])
            if extra_data:
                dat.update(extra_data)
                for identifier in app_data['program_special_identifier']:
                    if dat['filename'] == app_data.get(identifier):
                        dat['used'] = identifier
                dat['lang_display'] = language_choice_dict[dat['lang']]
            else:
                dat['remove_mark'] = True
        app_data['program_file_list'] = list(filter(lambda x: not x.get('remove_mark'), app_data['program_file_list']))
        for key, val in app_data['case'].items():
            val.update(get_case_metadata(self.session, key))
        # print(json.dumps(app_data, sort_keys=True, indent=4))
        return HttpResponse(json.dumps(app_data))


class BaseSessionPostMixin(BaseSessionMixin):

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(BaseSessionPostMixin, self).dispatch(request, *args, **kwargs)
        except Exception as e:
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return HttpResponse(json.dumps({"status": "reject", "message": "%s: %s" % (e.__class__.__name__, str(e))}))


class SessionSaveMeta(BaseSessionPostMixin, View):

    def post(self, request, sid):
        param_list = ['alias', 'time_limit', 'memory_limit', 'source', 'checker', 'interactor', 'validator', 'model',
                      'description', 'input', 'output', 'hint']
        kw = {x: request.POST[x] for x in param_list}
        kw.update(interactive=request.POST.get('interactive') == 'on')
        for param in ['checker', 'interactor', 'validator', 'model']:
            if kw[param] and not program_file_exists(self.session, kw[param]):
                raise ValueError("Program file does not exist")
        for param in ['description', 'input', 'output', 'hint']:
            if kw[param] and not statement_file_exists(self.session, kw[param]):
                raise ValueError("Statement file does not exist")
        self.config = update_config(self.config, **kw)
        dump_config(self.session, self.config)
        return response_ok()


class SessionCreateStatement(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename = request.POST['filename']
        create_statement_file(self.session, filename)
        return response_ok()


class SessionDeleteStatement(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename = request.POST['filename']
        delete_statement_file(self.session, filename)
        return response_ok()


class SessionGetStatementRaw(BaseSessionMixin, View):

    def get(self, request, sid):
        filename = request.GET['filename']
        return HttpResponse(read_statement_file(self.session, filename))


class SessionUpdateStatement(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename = request.POST['filename']
        text = request.POST['text']
        write_statement_file(self.session, filename, text)
        return response_ok()


class SessionUploadRegularFile(BaseSessionPostMixin, View):

    def post(self, request, sid):
        files = request.FILES.getlist('files[]')
        for file in files:
            used, all = load_volume(self.session)
            save_uploaded_file_to(file, path.join(settings.UPLOAD_DIR, str(self.session.problem_id)),
                                  filename=random_string(16), size_limit=all - used, keep_extension=True)
        return response_ok()


class SessionDeleteRegularFile(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename = request.POST['filename']
        try:
            upload_base_dir = path.join(settings.UPLOAD_DIR, str(self.session.problem_id))
            real_path = path.abspath(path.join(upload_base_dir, filename))
            if path.commonpath([real_path, upload_base_dir]) != upload_base_dir:
                raise ValueError("No... no... you are penetrating...")
            remove(real_path)
        except OSError:
            pass
        return response_ok()


class SessionCreateProgram(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename, type, lang, code = request.POST['filename'], request.POST['type'], \
                                     request.POST['lang'], request.POST['code']
        save_program_file(self.session, filename, type, lang, code)
        return response_ok()


class SessionUpdateProgram(BaseSessionPostMixin, View):

    def post(self, request, sid):
        raw_filename = request.POST['rawFilename']
        filename, type, lang, code = request.POST['filename'], request.POST['type'], \
                                     request.POST['lang'], request.POST['code']
        save_program_file(self.session, filename, type, lang, code, raw_filename)
        return response_ok()


class SessionReadProgram(BaseSessionMixin, View):

    def get(self, request, sid):
        filename = request.GET['filename']
        return HttpResponse(read_program_file(self.session, filename))


class SessionDeleteProgram(BaseSessionPostMixin, View):

    def post(self, request, sid):
        filename = request.POST['filename']
        delete_program_file(self.session, filename)
        return response_ok()


class SessionImportProgram(BaseSessionPostMixin, View):

    def post(self, request, sid):
        type = request.POST['type']
        sp = SpecialProgram.objects.get(builtin=True, filename=type)
        save_program_file(self.session, sp.filename, sp.category, sp.lang, sp.code)
        return response_ok()


class SessionCreateCaseManually(BaseSessionPostMixin, View):

    def post(self, request, sid):
        input = request.POST['input']
        output = request.POST['output']
        well_form = request.POST.get("wellForm") == "on"
        if well_form:
            input, output = well_form_text(input), well_form_text(output)
        if not input:
            raise ValueError('Input file cannot be empty')
        save_case(self.session, input.encode(), output.encode(), well_form=well_form)
        return response_ok()


class SessionUpdateOrders(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = json.loads(request.POST['case'])
        unused = json.loads(request.POST['unused'])
        conclusion = dict()
        for order, k in enumerate(case, start=1):
            conclusion[k['fingerprint']] = order
        for k in unused:
            conclusion[k['fingerprint']] = 0
        reorder_case(self.session, conclusion)
        return response_ok()


class SessionPreviewCase(BaseSessionMixin, View):

    def get(self, request, sid):
        fingerprint = request.GET['case']
        return HttpResponse(json.dumps(preview_case(self.session, fingerprint)))


class SessionUploadCase(BaseSessionPostMixin, View):

    def post(self, request, sid):
        file = request.FILES['file']
        file_directory = '/tmp'
        file_path = save_uploaded_file_to(file, file_directory, filename=random_string(), keep_extension=True)
        process_uploaded_case(self.session, file_path)
        remove(file_path)
        return response_ok()


class SessionReformCase(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['fingerprint']
        inputOnly = request.POST.get('inputOnly') == 'on'
        reform_case(self.session, case, only_input=inputOnly)
        return response_ok()


class SessionUpdateCasePoint(BaseSessionPostMixin, View):

    def post(self, request, sid):
        point = request.POST['point']
        case = request.POST['fingerprint']
        readjust_case_point(self.session, case, int(point))
        return response_ok()


class SessionValidateCase(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['fingerprint']
        validator = request.POST['program']
        return response_ok(run_id=validate_case("Validate a case", self.session, validator, case))


class SessionRunCaseOutput(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['fingerprint']
        model = request.POST['program']
        return response_ok(run_id=get_case_output("Run case output", self.session, model, case))


class SessionCheckCaseOutput(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['fingerprint']
        submission = request.POST['program']
        checker = request.POST['checker']
        return response_ok(run_id=check_case("Check a case", self.session, submission, checker, case))


class SessionValidateAllCase(BaseSessionPostMixin, View):

    def post(self, request, sid):
        validator = request.POST['program']
        return response_ok(run_id=validate_case("Validate all cases", self.session, validator))


class SessionRunAllCaseOutput(BaseSessionPostMixin, View):

    def post(self, request, sid):
        model = request.POST['program']
        return response_ok(run_id=get_case_output("Run all case outputs", self.session, model))


class SessionCheckAllCaseOutput(BaseSessionPostMixin, View):

    def post(self, request, sid):
        submission = request.POST['program']
        checker = request.POST['checker']
        return response_ok(run_id=check_case("Check all cases", self.session, submission, checker))


class SessionDeleteCase(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['fingerprint']
        delete_case(self.session, case)
        return response_ok()


class SessionDownloadInput(BaseSessionMixin, View):

    def get(self, request, sid):
        case = request.GET['fingerprint']
        input, _ = get_test_file_path(self.session, case)
        return respond_as_attachment(request, input, case + '.in')


class SessionDownloadOutput(BaseSessionMixin, View):

    def get(self, request, sid):
        case = request.GET['fingerprint']
        _, output = get_test_file_path(self.session, case)
        return respond_as_attachment(request, output, case + '.in')


class SessionGenerateInput(BaseSessionPostMixin, View):

    def post(self, request, sid):
        case = request.POST['program']
        raw_param = request.POST['param']
        return response_ok()
