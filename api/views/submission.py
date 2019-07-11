from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from api.views.pagination import StandardResultsSetPagination
from contest.models import Contest
from submission.models import Submission
from utils.permission import is_contest_manager


class SubmissionRecordSerializer(serializers.ModelSerializer):
  class Meta:
    model = Submission
    fields = ("author_id", "contest_id", "problem_id", "create_time", "status")


class SubmissionListView(ListAPIView):
  permission_classes = (IsAuthenticated,)
  throttle_classes = (UserRateThrottle,)
  serializer_class = SubmissionRecordSerializer
  pagination_class = StandardResultsSetPagination

  def get_queryset(self):
    contest_id = self.request.data.get("contest")
    if contest_id:
      contest = Contest.objects.get(contest_id)
      if is_contest_manager(self.request.user, contest):
        submission_set = contest.submission_set.all()
      else:
        raise PermissionDenied
    else:
      submission_set = Submission.objects.select_related("problem").filter(problem__visible=True).all()
    return submission_set.only("author_id", "contest_id", "problem_id", "create_time", "status")
