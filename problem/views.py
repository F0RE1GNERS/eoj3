import json
from django.shortcuts import render, HttpResponse, reverse, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic import TemplateView, View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q

from django.core.exceptions import PermissionDenied
from tagging.models import Tag, TaggedItem, ContentType
from collections import Counter

from .models import Problem
from .tasks import get_many_problem_accept_count, create_submission, judge_submission_on_problem
from submission.forms import SubmitForm
from submission.models import Submission, SubmissionStatus
from dispatcher.tasks import submit_code
from account.permissions import is_admin_or_root
from utils.authentication import test_site_open
from utils.language import LANG_CHOICE


class ProblemList(ListView):
    template_name = 'problem/index.jinja2'
    paginate_by = 100
    context_object_name = 'problem_list'

    def get_queryset(self):
        kw = self.request.GET.get('keyword')
        tg = self.request.GET.get('tag')
        if tg:
            queryset = TaggedItem.objects.get_by_model(Problem, get_object_or_404(Tag, name=tg))
        else:
            queryset = Problem.objects.all()
        if not is_admin_or_root(self.request.user):
            queryset = queryset.filter(visible=True)

        if kw:
            q = Q(title__icontains=kw) | Q(source__icontains=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw)
            queryset = queryset.filter(q)
            if not self.request.user.is_authenticated or self.request.user.show_tags:
                tag = Tag.objects.filter(name=kw)
                if tag.exists():
                    queryset = (queryset | TaggedItem.objects.get_by_model(Problem, tag.first())).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        data = super(ProblemList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        show_tags = True
        current_problem_set = [problem.pk for problem in data['problem_list']]
        if self.request.user.is_authenticated:
            show_tags = self.request.user.show_tags
            # Get AC / Wrong
            submission_list = self.request.user.submission_set.only('pk', 'author_id', 'problem_id', 'status'). \
                filter(problem_id__in=current_problem_set).all()
            submission_set = dict()
            for submission in submission_list:
                if submission_set.get(submission.problem_id) != 'success':
                    if submission.status != SubmissionStatus.ACCEPTED:
                        submission_set[submission.problem_id] = 'danger'
                    else:
                        submission_set[submission.problem_id] = 'success'
            for problem in data['problem_list']:
                if submission_set.get(problem.pk) is not None:
                    problem.status = submission_set.get(problem.pk)

        # Get Accepted of all users
        accept_count = get_many_problem_accept_count(list(map(lambda x: x.id, data['problem_list'])))
        for problem in data['problem_list']:
            problem.accept_count = accept_count[problem.id]

        # Get tags
        if show_tags:
            tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                                .filter(object_id__in=current_problem_set))
            for problem in data['problem_list']:
                items = list(filter(lambda x: x.object_id == problem.pk, tagged_items))
                if items:
                    problem.my_tags = map(lambda x: x.tag.name, items)

        return data


class ProblemDetailMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(Problem, **kwargs)
        self.user = request.user
        self.request = request
        return super(ProblemDetailMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if is_admin_or_root(self.user) and self.problem.problemmanagement_set.filter(user=self.user).exists():
            return True
        return self.problem.visible

    def get_context_data(self, **kwargs):
        data = super(ProblemDetailMixin, self).get_context_data(**kwargs)
        data['problem'] = self.problem
        return data


class ProblemView(ProblemDetailMixin, TemplateView):

    template_name = 'problem/detail/problem.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ProblemView, self).get_context_data()
        if not is_admin_or_root(self.request.user) and not self.problem.visible:
            raise PermissionDenied("You don't have the access.")
        data['problem'] = self.problem

        show_tags = True
        if self.request.user.is_authenticated:
            show_tags = self.request.user.show_tags
        if show_tags:
            data['tags'] = self.problem.tags

        return data


class ProblemSubmitView(ProblemDetailMixin, TemplateView):

    template_name = 'problem/detail/submit.jinja2'

    def test_func(self):
        return super(ProblemSubmitView, self).test_func() and self.user.is_authenticated

    def get_context_data(self, **kwargs):
        data = super(ProblemSubmitView, self).get_context_data(**kwargs)
        data['lang_choices'] = LANG_CHOICE
        return data

    def post(self, request, pk):
        submission = create_submission(self.problem, self.user, request.POST['code'], request.POST['lang'])
        judge_submission_on_problem(submission)
        return HttpResponse()


class StatusList(ListView):
    template_name = 'problem/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        kw = self.request.GET.get('keyword')
        author = self.request.GET.get('author')
        prob = self.request.GET.get('problem')
        queryset = Submission.objects.select_related('problem', 'author').only('pk', 'contest_id', 'create_time',
                                                                               'author_id', 'author__username',
                                                                               'author__nickname', 'author__magic',
                                                                               'problem_id', 'problem__title', 'lang',
                                                                               'status', 'status_percent', 'status_time',
                                                                               'status_memory')
        if not is_admin_or_root(self.request.user):
            queryset = queryset.filter(contest__isnull=True, problem__visible=True)
        if author and author.isdigit():
            queryset = queryset.filter(author_id=author)
        if prob and prob.isdigit():
            queryset = queryset.filter(problem_id=prob)
        if kw:
            q = Q(author__username__iexact=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw) | Q(problem__pk__exact=kw)
            queryset = queryset.filter(q)
        return queryset.all()[:10000]

    def get_context_data(self, **kwargs):
        data = super(StatusList, self).get_context_data(**kwargs)
        user = self.request.user
        # print(reverse('status') + '?keyword=' + str(1))
        data['keyword'] = self.request.GET.get('keyword')
        if user.is_authenticated:
            for submission in data['submission_list']:
                if is_admin_or_root(user) or submission.author == user:
                    submission.is_privileged = True
        return data


class ProblemPersonalSubmissionAPI(ProblemDetailMixin, View):

    def test_func(self):
        return super(ProblemPersonalSubmissionAPI, self).test_func() and self.user.is_authenticated

    def get(self, request, pk):
        subs = []
        SUB_FIELDS = ["id", "lang", "code_as_html", "create_time_display", "judge_time_display",
                      "status", "status_detail_list", "code", "status_time", "status_message"]
        for sub in self.problem.submission_set.filter(author=self.user).order_by("-create_time").all():
            subs.append({k: getattr(sub, k) for k in SUB_FIELDS})
        return HttpResponse(json.dumps(subs))
