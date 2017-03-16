import json
from django.shortcuts import render
from .models import Submission, get_color_from_status

def submission_view(request, pk):
    submission = Submission.objects.get(pk=pk)
    context = {'submission': submission}
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
