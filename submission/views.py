import json
from django.shortcuts import render, reverse, get_object_or_404, HttpResponseRedirect
from django.views.generic.list import ListView
from django.views.generic import View
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter

from account.permissions import is_admin_or_root
from .models import Submission, get_color_from_status, SubmissionStatus
from dispatcher.tasks import send_rejudge
from utils.authentication import test_site_open


class SubmissionView(UserPassesTestMixin, View):

    def dispatch(self, request, *args, **kwargs):
        self.submission = get_object_or_404(Submission, pk=kwargs.get('pk'))
        return super(SubmissionView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if is_admin_or_root(user):
            return True
        if self.submission.contest_id and self.submission.contest.get_status() == 'running':
            return True
        if not test_site_open(self.request):
            raise PermissionDenied("Site is closed now.")
        if self.submission.author != user:
            raise PermissionDenied("You don't have access to this code.")
        return True

    def get(self, request, pk):
        context = dict(submission=self.submission)
        context['code'] = highlight(self.submission.code, get_lexer_by_name(self.submission.lang), HtmlFormatter())
        if is_admin_or_root(request.user):
            context['is_privileged'] = True
        if SubmissionStatus.is_judged(self.submission.status):
            context['is_judged'] = True
        if self.submission.status == SubmissionStatus.COMPILE_ERROR:
            context['detail_ce'] = self.submission.status_detail
        if self.submission.contest is not None:
            try:
                context['contest_problem'] = self.submission.contest.contestproblem_set.\
                    get(problem_id=self.submission.problem_id)
            except:
                context['contest_problem'] = 'N/A'
            if not is_admin_or_root(request.user):
                context['is_frozen'] = self.submission.contest.get_frozen()
        try:
            detail_msg = self.submission.status_detail
            if detail_msg == '':
                raise ValueError
            detail = json.loads(detail_msg)
            for d in detail:
                d['color'] = get_color_from_status(d['verdict'])
            detail.sort(key=lambda x: x['count'])
            context['detail'] = detail
        except ValueError:
            pass
        except Exception as e:
            print(repr(e))
        return render(request, 'submission.jinja2', context=context)


class StatusList(ListView):
    template_name = 'status.jinja2'
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
        if author:
            queryset = queryset.filter(author__username=author)
        if prob:
            queryset = queryset.filter(problem_id=prob)
        if kw:
            q = Q(author__username__iexact=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw) | Q(problem__pk__exact=kw)
            queryset = queryset.filter(q)
        return queryset.all()

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


class SubmissionRejudgeView(UserPassesTestMixin, View):
    def test_func(self):
        if not is_admin_or_root(self.request.user):
            self.permission_denied_message = "You don't have the access."
            return False
        return True

    def get(self, request, pk):
        send_rejudge(pk)
        return HttpResponseRedirect(reverse('submission', kwargs={'pk': pk}))
