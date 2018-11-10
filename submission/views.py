import datetime
import json
from base64 import b64decode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import render, reverse, get_object_or_404, HttpResponseRedirect, HttpResponse
from django.template import loader, Context
from django.views.generic import View
from os import path
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from account.models import User
from account.permissions import is_admin_or_root
from contest.models import ContestProblem
from dispatcher.models import Server
from utils.permission import get_permission_for_submission
from .models import Submission
from submission.util import SubmissionStatus


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


def render_submission(submission: Submission, permission=1, hide_problem=False, show_percent=False,
                      rejudge_available=True) -> str:
    if permission == 0:
        raise PermissionDenied
    if permission == 1 and submission.status != SubmissionStatus.COMPILE_ERROR and submission.status_message:
        submission.status_message = ''
    try:
        judge_server = Server.objects.get(pk=submission.judge_server).name
    except:
        judge_server = ''
    t = loader.get_template('components/single_submission.jinja2')
    c = Context({'submission': submission, 'hide_problem': hide_problem, 'show_percent': show_percent,
                 'server': judge_server, 'rejudge_authorized': permission >= 2 and rejudge_available})
    return t.render(c)


def render_submission_report(pk):
    try:
        with open(path.join(settings.GENERATE_DIR, 'submission-%d' % pk), 'r') as report_file:
            ans = []
            for line in report_file:
                meta, *b64s = line.split('|')
                if len(b64s) == 4:
                    input, output, answer, checker = map(lambda txt: b64decode(txt.encode()).decode(), b64s)
                    stderr = ""
                else:
                    input, output, stderr, answer, checker = map(lambda txt: b64decode(txt.encode()).decode(), b64s)
                ans.append({'meta': meta, 'input': input, 'output': output, 'stderr': stderr, 'answer': answer, 'checker': checker})
        t = loader.get_template('components/submission_report.jinja2')
        return t.render(Context({'testcases': ans}))
    except (FileNotFoundError, ValueError):
        return ''


def submission_count_api(request, name):
    user = get_object_or_404(User, username=name)
    now = datetime.datetime.now()
    one_year_ago = now.replace(year=now.year - 1)
    submissions = Submission.objects.filter(author=user, create_time__gte=one_year_ago)
    result = {submission.create_time.timestamp(): 1 for submission in submissions}
    return JsonResponse(result)
