import json
from django.shortcuts import render
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


class SubmissionView(UserPassesTestMixin, View):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if not is_admin_or_root(user) and Submission.objects.get(pk=self.kwargs.get('pk')).author != user:
            raise PermissionDenied("You don't have access to this code.")

    def get(self, request, pk):
        submission = Submission.objects.get(pk=pk)
        context = dict(submission=submission)
        context['code'] = highlight(submission.code, get_lexer_by_name(submission.lang), HtmlFormatter())
        if submission.status == SubmissionStatus.COMPILE_ERROR:
            context.update({'detail_ce': submission.status_detail})
        else:
            try:
                detail_msg = submission.status_detail
                if detail_msg == '':
                    raise ValueError
                detail = json.loads(detail_msg)
                for d in detail:
                    d['color'] = get_color_from_status(d['verdict'])
                detail.sort(key=lambda x: x['count'])
                # print(detail)
                context.update({'detail': detail})
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
        if is_admin_or_root(self.request.user):
            queryset = Submission.objects.filter(contest__isnull=True)
        else:
            queryset = Submission.objects.filter(contest__isnull=True, problem__visible=True)
        if kw:
            q = Q(author__username__iexact=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw) | Q(problem__pk__exact=kw)
            queryset = queryset.filter(q)
        return queryset.all()

    def get_context_data(self, **kwargs):
        data = super(StatusList, self).get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            for submission in data['submission_list']:
                if is_admin_or_root(user) or submission.author == user:
                    submission.is_privileged = True
        return data
