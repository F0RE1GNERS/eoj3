import datetime
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import render, reverse, get_object_or_404, HttpResponseRedirect, HttpResponse
from django.template import loader, Context
from django.views.generic import View
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from account.models import User
from account.permissions import is_admin_or_root
from contest.models import ContestProblem
from dispatcher.tasks import send_rejudge
from utils.permission import get_permission_for_submission
from .models import Submission, SubmissionStatus


@login_required
def submission_code_api(request):
    c = request.GET.get('c')
    p = request.GET.get('p')
    try:
        if c:
            p = ContestProblem.objects.get(contest_id=c, identifier=p).problem_id
            submission = request.user.submission_set.filter(contest_id=c, problem_id=p).first()
        else:
            submission = request.user.submission_set.filter(problem_id=p).first()
        code = submission.code
    except (AttributeError, ValueError, ContestProblem.DoesNotExist):
        code = ''
    return HttpResponse(code, content_type='text_plain')


def render_submission(submission: Submission, permission=1, hide_problem=False, show_percent=False) -> str:
    if permission == 0:
        raise PermissionDenied
    if permission == 1 and submission.status_private != SubmissionStatus.COMPILE_ERROR and submission.status_message:
        submission.status_message = ''
    t = loader.get_template('components/single_submission.jinja2')
    c = Context({'submission': submission, 'hide_problem': hide_problem, 'show_percent': show_percent})
    return t.render(c)


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
                if self.submission.contest.rule == 'acm':
                    context['is_not_detailed'] = True
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


class SubmissionRejudgeView(UserPassesTestMixin, View):
    def test_func(self):
        if not is_admin_or_root(self.request.user):
            self.permission_denied_message = "You don't have the access."
            return False
        return True

    def get(self, request, pk):
        send_rejudge(pk)
        return HttpResponseRedirect(reverse('submission', kwargs={'pk': pk}))


def submission_count_api(request, name):
    user = get_object_or_404(User, username=name)
    now = datetime.datetime.now()
    one_year_ago = now.replace(year=now.year - 1)
    submissions = Submission.objects.filter(author=user, create_time__gte=one_year_ago)
    result = {submission.create_time.timestamp(): 1 for submission in submissions}
    return JsonResponse(result)
