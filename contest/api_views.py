from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from contest.models import Contest
from problem.models import Problem
from submission.models import Submission
from dispatcher.tasks import DispatcherThread


class ContestSubmitAPI(APIView):
    def post(self, request):
        print(request.user)
        if not request.user.is_authenticated():
            Response("please login")
        lang = request.data.get('lang')
        code = request.data.get('code')
        cid = request.data.get('cid')
        pid = request.data.get('pid')
        contest = Contest.objects.get(pk=cid)
        with transaction.atomic():
            contest_problem = contest.contestproblem_set.select_for_update().get(identifier=pid)
            problem = Problem.objects.select_for_update().get(pk=contest_problem.problem.pk)
            submission = Submission.objects.create(lang=lang,
                                                   code=code,
                                                   contest=contest,
                                                   # contest_problem=contest_problem,
                                                   problem=problem,
                                                   author=request.user)
            # submission.author = self.request.user
            submission.code_length = len(submission.code)
            submission.save()

            contest_problem.add_submit()
            submission.problem.add_submit()
            contest_problem.save()
            submission.problem.save()

            DispatcherThread(submission.problem.pk, submission.pk).start()
        return Response({'status', 'accept'})
