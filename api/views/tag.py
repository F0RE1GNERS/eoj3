from django.http import HttpResponse
import json

from problem.models import Problem


def return_problems(request):
    if request.method == "GET":
        tag = request.GET.get("tag", default="tree")

        problems = Problem.objects.filter(visible=True)

        ids = []

        for problem in problems:
            tags = [tag.name for tag in problem.tags]
            if tag in tags:
                ids.append(problem.id)

        problem_dic = {"problems": ids}

        return HttpResponse(json.dumps(problem_dic), content_type="application/json")
