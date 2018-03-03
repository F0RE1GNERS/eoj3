import json

from django.views.generic import ListView
from django.views.generic import TemplateView

from polygon.problem2.views.base import ProblemRevisionMixin


class TaskList(ProblemRevisionMixin, ListView):
    template_name = 'polygon/problem2/task/list.jinja2'
    context_object_name = 'task_list'

    def get_queryset(self):
        return self.revision.task_set.all().defer("report").order_by("-id")


class TaskPreview(ProblemRevisionMixin, TemplateView):
    template_name = 'polygon/problem2/task/preview.jinja2'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["task"] = self.revision.task_set.get(id=kwargs["tpk"])
        data["disable_grid"] = True
        try:
            data["task"].pretty_report = json.dumps(json.loads(data["task"].report), indent=2, sort_keys=True)
        except json.JSONDecodeError:
            data["task"].pretty_report = ""
        return data
