from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from problem.models import Problem


class ProblemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ["problem_list_info"]

    problem_list_info = serializers.SerializerMethodField()

    def get_problem_list_info(self, problem):
        problems = Problem.objects.filter(visible=True).order_by("id")
        return [str(prob) for prob in problems]


class ProblemListView(RetrieveAPIView):
    queryset = Problem.objects.filter(visible=True)
    serializer_class = ProblemListSerializer
