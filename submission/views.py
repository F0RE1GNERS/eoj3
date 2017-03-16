import json
from django.shortcuts import render
from .models import Submission, get_color_from_status
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter


def submission_view(request, pk):
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
    return render(request, 'submission.html', context=context)


def status_view(request):
    submissions = Submission.objects.all()
    return render(request, 'status.html', context={'submission_list': submissions})
