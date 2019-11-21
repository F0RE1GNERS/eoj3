import json

from django.http import HttpResponse
from tagging.models import TaggedItem

from problem.models import Problem


def return_problems(request):
  if request.method == "GET":
    tag = request.GET.get("tag", default="tree")
    queryset = TaggedItem.objects.get_by_model(Problem, tag)
    problem_id_dic = {"problems": list(queryset.values_list("id", flat=True))}
    return HttpResponse(json.dumps(problem_id_dic), content_type="application/json")
