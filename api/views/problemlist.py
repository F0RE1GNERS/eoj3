from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from problem.models import Problem


class ProblemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ["problem_list_info"]

    problem_list_info = serializers.SerializerMethodField()

    def get_problem_list_info(self, problem):
        return list(zip([_id[0] for _id in Problem.objects.values_list("id")[:]],
                        [title[0] for title in Problem.objects.values_list("title")[:]]))


class ProblemListView(RetrieveAPIView):
    queryset = Problem.objects.all()
    serializer_class = ProblemListSerializer
