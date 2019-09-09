from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from problem.models import Problem


class ProblemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ["problem_list_info"]

    problem_list_info = serializers.SerializerMethodField()

    def get_problem_list_info(self, problem):
        problems = Problem.objects.all().order_by("id")
        ids = [_id[0] for _id in problems.values_list("id")[:]]
        titles = [title[0] for title in problems.values_list("title")[:]]
        id_titles = []
        space_between = ".   "
        for i in range(len(ids)):
            id_titles.append(str(ids[i]) + space_between + str(titles[i]))

        return id_titles


class ProblemListView(RetrieveAPIView):
    queryset = Problem.objects.filter(visible=True)
    serializer_class = ProblemListSerializer
