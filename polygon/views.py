import json

from django.contrib import messages
from django.contrib.auth import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.views.generic import ListView, View, DetailView, TemplateView
from django.views.generic.base import TemplateResponseMixin, ContextMixin

from account.permissions import is_admin_or_root
from problem.models import Problem, ProblemManagement
from .models import EditSession
from .session import (
    init_session, pull_session, load_config, normal_regex_check, update_config, dump_config,
    load_statement_file_list, create_statement_file, delete_statement_file, read_statement_file, write_statement_file
)


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


def response_ok():
    return HttpResponse(json.dumps({"status": "received"}))


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
        return data


class SessionEditUpdateAPI(BaseSessionMixin, View):

    def get(self, request, sid):
        data = self.get_context_data(sid=sid)
        app_data = data['config']
        app_data['problem_id'] = self.problem.id
        app_data['case_count'] = len(list(filter(lambda x: x.get('order'), app_data['case'].items())))
        app_data['pretest_count'] = len(list(filter(lambda x: x.get('pretest'), app_data['case'].items())))
        app_data['sample_count'] = len(list(filter(lambda x: x.get('sample'), app_data['case'].items())))
        app_data['statement_file_list'] = load_statement_file_list(self.session)
        app_data['statement_identifier'] = ['description', 'input', 'output', 'hint']
        for dat in app_data['statement_file_list']:
            for identifier in app_data['statement_identifier']:
                if dat['filename'] == app_data[identifier]:
                    dat['used'] = identifier
        print(app_data)
        return HttpResponse(json.dumps(app_data))


class BaseSessionPostMixin(BaseSessionMixin):

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(BaseSessionPostMixin, self).dispatch(request, *args, **kwargs)
        except Exception as e:
            return HttpResponse(json.dumps({"status": "reject", "message": str(e)}))


class SessionSaveMeta(BaseSessionPostMixin, View):

    def post(self, request, sid):
        alias = request.POST['alias']
        time_limit = request.POST['time_limit']
        memory_limit = request.POST['memory_limit']
        source = self.request.POST['source']
        self.config = update_config(self.config, alias=alias, time_limit=time_limit, memory_limit=memory_limit,
                                    source=source)
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
