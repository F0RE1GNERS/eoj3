from django.template import loader, Context
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from problem.models import Problem


class ProblemSerializer(serializers.ModelSerializer):
  class Meta:
    model = Problem
    fields = ("id", "title", "tags", "statement", "level", "ac_user_count", "total_user_count", "ac_count",
              "total_count", "reward")

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
