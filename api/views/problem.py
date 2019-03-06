from django.template import loader, Context
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from api.views.pagination import StandardResultsSetPagination
from contest.models import Contest
from problem.models import Problem
from submission.models import Submission
from utils.permission import is_contest_manager


class ProblemSerializer(serializers.ModelSerializer):
  class Meta:
    model = Problem
    fields = ("id", "title", "tags", "statement")

  tags = serializers.SerializerMethodField()
  statement = serializers.SerializerMethodField()

  def get_tags(self, problem):
    return [tag.name for tag in problem.tags]

  def get_statement(self, problem):
    t = loader.get_template('api/problem.jinja2')
    return t.render(Context({"problem": problem}))


class ProblemView(RetrieveAPIView):
  queryset = Problem.objects.filter(visible=True)
  serializer_class = ProblemSerializer
