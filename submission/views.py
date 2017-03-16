from django.shortcuts import render
from .models import Submission

def submission_view(request, pk):
    submission = Submission.objects.get(pk=pk)
    return render(request, 'submission.html', context={'submission': submission})
