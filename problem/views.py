import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import HttpResponse, get_object_or_404, reverse, render
from django.views.generic import TemplateView, View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.list import ListView
from tagging.models import Tag, TaggedItem, ContentType

from account.models import User
from account.permissions import is_admin_or_root
from submission.models import Submission, SubmissionStatus, STATUS_CHOICE
from submission.views import render_submission
from submission.statistics import get_accept_problem_list, get_attempted_problem_list
from utils.language import LANG_CHOICE
from .models import Problem
from .permission import has_permission_for_problem_management
from .statistics import (
    get_many_problem_accept_count, get_problem_accept_count, get_problem_accept_ratio, get_problem_accept_user_count,
    get_problem_accept_user_ratio, get_problem_all_count, get_problem_all_user_count, get_many_problem_difficulty,
    get_problem_difficulty
)
from .tasks import create_submission, judge_submission_on_problem


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
        current_problem_set = [problem.pk for problem in data['problem_list']]
        for problem in data['problem_list']:
            problem.personal_label = 0
        if self.request.user.is_authenticated:
            # Get AC / Wrong
            attempt_list = set(get_attempted_problem_list(self.request.user.id))
            accept_list = set(get_accept_problem_list(self.request.user.id))
            for problem in data['problem_list']:
                if problem.id in accept_list:
                    problem.personal_label = 1
                elif problem.id in attempt_list:
                    problem.personal_label = -1

        # Get Accepted of all users
        problem_ids = list(map(lambda x: x.id, data['problem_list']))
        accept_count = get_many_problem_accept_count(problem_ids)
        difficulties = get_many_problem_difficulty(problem_ids)
        for problem in data['problem_list']:
            problem.accept_count = accept_count[problem.id]
            problem.difficulty = difficulties[problem.id]

        # Get tags
        tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                            .filter(object_id__in=current_problem_set).select_related("tag"))
        for problem in data['problem_list']:
            items = list(filter(lambda x: x.object_id == problem.pk, tagged_items))
            if items:
                problem.my_tags = map(lambda x: x.tag.name, items)

        return data


class ProblemDetailMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
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
        return HttpResponse(json.dumps({"url": reverse('problem:submission_api',
                                                       kwargs={'pk': self.problem.id, 'sid': submission.id})}))


class ProblemStatisticsView(ProblemDetailMixin, TemplateView):

    template_name = 'problem/detail/statistics.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ProblemStatisticsView, self).get_context_data(**kwargs)
        data['user_ac_count'] = get_problem_accept_user_count(self.problem.id)
        data['user_all_count'] = get_problem_all_user_count(self.problem.id)
        data['user_ratio'] = get_problem_accept_user_ratio(self.problem.id)
        data['ac_count'] = get_problem_accept_count(self.problem.id)
        data['all_count'] = get_problem_all_count(self.problem.id)
        data['ratio'] = get_problem_accept_ratio(self.problem.id)
        data['difficulty'] = get_problem_difficulty(self.problem.id)
        return data


class StatusList(ListView):

    template_name = 'problem/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'
    allow_problem_query = True

    def get_selected_from(self):
        return Submission.objects.all()

    def reinterpret_problem_identifier(self, value):
        return value

    def get_queryset(self):
        queryset = self.get_selected_from().select_related('problem', 'author').\
            only('pk', 'contest_id', 'create_time', 'author_id', 'author__username', 'author__magic', 'problem_id',
                 'problem__title', 'lang', 'status', 'status_time')
        if not is_admin_or_root(self.request.user):
            queryset = queryset.filter(contest__isnull=True, problem__visible=True)

        if 'user' in self.request.GET:
            queryset = queryset.filter(author_id=self.request.GET['user'])
        if self.allow_problem_query and 'problem' in self.request.GET:
            queryset = queryset.filter(problem_id=self.reinterpret_problem_identifier(self.request.GET['problem']))
        if 'lang' in self.request.GET:
            queryset = queryset.filter(lang=self.request.GET['lang'])
        if 'verdict' in self.request.GET:
            queryset = queryset.filter(status=int(self.request.GET['verdict'][1:]))
        #
        # if kw:
        #     q = Q(author__username__iexact=kw)
        #     if kw.isdigit():
        #     q |= Q(pk__exact=kw) | Q(problem__pk__exact=kw)
        #     queryset = queryset.filter(q)
        return queryset.all()[:10000]

    def get_context_data(self, **kwargs):
        data = super(StatusList, self).get_context_data(**kwargs)
        user = self.request.user
        data['keyword'] = self.request.GET.get('keyword')
        data['param_verdict'], data['param_lang'], data['param_user'], data['param_problem'] = \
            self.request.GET.get('verdict', ''), self.request.GET.get('lang', ''),\
            self.request.GET.get('user', ''), self.request.GET.get('problem', '')
        data['lang_choices'] = LANG_CHOICE
        data['verdict_choices'] = STATUS_CHOICE

        if user.is_authenticated:
            for submission in data['submission_list']:
                if is_admin_or_root(user) or submission.author == user:
                    submission.is_privileged = True
        return data


class ProblemPersonalSubmissionAPI(UserPassesTestMixin, TemplateView):

    template_name = 'components/single_submission.jinja2'

    def test_func(self):
        return self.request.user.is_authenticated

    def get_context_data(self, **kwargs):
        submission = Submission.objects.get(problem_id=self.kwargs.get('pk'), author=self.request.user,
                                            pk=self.kwargs.get('sid'))
        return {'submission': submission, 'hide_problem': True}


class ProblemPersonalOlderSubmissionsAPI(UserPassesTestMixin, TemplateView):

    template_name = 'components/past_submissions.jinja2'

    def test_func(self):
        return self.request.user.is_authenticated

    def get_context_data(self, **kwargs):
        submission_set = Submission.objects.only("problem_id", "id", "status", "create_time",
                                                 "author_id", "author__username", "author__magic"). \
            filter(author_id=self.request.user.pk, problem_id=kwargs.get('pk'))
        return {'submission_list': submission_set}


class ProblemSubmissionView(TemplateView):

    template_name = 'submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ProblemSubmissionView, self).get_context_data(**kwargs)
        data['submission'] = submission = Submission.objects.get(pk=self.kwargs.get('sid'),
                                                                 problem_id=self.kwargs.get('pk'))
        if self.request.user.is_authenticated and (
                            submission.author == self.request.user or
                        has_permission_for_problem_management(self.request.user,
                                                              submission.problem) or
                    self.request.user.submission_set.filter(
                        problem_id=self.kwargs.get('pk'),
                        status=SubmissionStatus.ACCEPTED).exists()):
            submission_block = render_submission(submission)
        else:
            submission_block = 'You are not authorized to view this submission.'
        data['submission_block'] = submission_block
        data['problem'] = submission.problem
        return data


class Millionaires(ListView):
    template_name = 'problem/standings.jinja2'
    paginate_by = 100
    context_object_name = 'rank_list'

    def get_queryset(self):
        return User.objects.only("username", "magic", "score").filter(score__gt=0)

    def get_context_data(self, **kwargs):
        data = super(Millionaires, self).get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            data['my_rank'] = 'N/A'
        else:
            data['my_rank'] = User.objects.filter(score__gte=self.request.user.score).count()
        return data
