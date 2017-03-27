import shortuuid
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import HttpResponseRedirect, render, reverse
from submission.models import Submission
from account.models import User
from contest.models import Contest
from dispatcher.tasks import submit_code_for_contest, submit_code


@csrf_exempt
def test_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        rstring = shortuuid.ShortUUID().random(6)
        email = '%s@%s.%s' % (rstring, rstring, rstring)
        user, _ = User.objects.get_or_create(username=username, defaults={'username': username,
                                                                          'email': email})
        submission = Submission()
        submission.lang = request.POST['lang']
        submission.code = request.POST['code']
        problem = request.POST['problem']
        submit_code(submission, user, problem)
        return render(request, 'blank.jinja2')


@csrf_exempt
def test_contest_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        rstring = shortuuid.ShortUUID().random(6)
        email = '%s@%s.%s' % (rstring, rstring, rstring)
        user, _ = User.objects.get_or_create(username=username, defaults={'username': username,
                                                                          'email': email})
        submission = Submission()
        submission.lang = request.POST['lang']
        submission.code = request.POST['code']
        contest = Contest.objects.get(pk=request.POST['contest'])
        problem = request.POST['problem']
        submit_code_for_contest(submission, user, problem, contest)
        return render(request, 'blank.jinja2')
