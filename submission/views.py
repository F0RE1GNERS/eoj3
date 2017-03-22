import json
from django.shortcuts import render
from django.views.generic.list import ListView
from django.views.generic import View
from django.contrib.auth.mixins import UserPassesTestMixin
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter

from account.models import Privilege
from .models import Submission, get_color_from_status


class SubmissionView(UserPassesTestMixin, View):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.privilege in (Privilege.ROOT, Privilege.ADMIN)
                                          or Submission.objects.get(pk=self.kwargs.get('pk')).author == user)

    def get(self, request, pk):
        submission = Submission.objects.get(pk=pk)
        context = dict(submission=submission)
        context['code'] = highlight(submission.code, get_lexer_by_name(submission.lang), HtmlFormatter())
        try:
            detail_msg = submission.status_detail
            if detail_msg == '':
                raise ValueError
            detail = json.loads(detail_msg)
            for d in detail:
                d['color'] = get_color_from_status(d['verdict'])
            detail.sort(key=lambda x: x['count'])
            print(detail)
            context.update({'detail': detail})
        except ValueError:
            pass
        except Exception as e:
            print(e)
        return render(request, 'submission.jinja2', context=context)



class StatusList(ListView):
    template_name = 'status.jinja2'
    queryset = Submission.objects.filter(contest__isnull=True).all()
    paginate_by = 50
    context_object_name = 'submission_list'
