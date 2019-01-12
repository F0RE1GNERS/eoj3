import json

from django.http import Http404
from django.views.generic import ListView
from django.views.generic import TemplateView

from polygon.models import Program
from polygon.problem2.views.base import ProblemRevisionMixin
from utils.language import transform_code_to_html


class TaskList(ProblemRevisionMixin, ListView):
    template_name = 'problem2/task/list.jinja2'
    context_object_name = 'task_list'
    polygon_title = "任务"

    def get_queryset(self):
        return self.revision.task_set.all().defer("report").order_by("-id")


class TaskPreview(ProblemRevisionMixin, TemplateView):
    template_name = 'problem2/task/preview.jinja2'
    polygon_title = "任务详情"

    def render_to_response(self, context, **response_kwargs):
        try:
            return super().render_to_response(context, **response_kwargs)
        except:
            context["tag"] = "PRETTY"  # fallback rendering option
            return super().render_to_response(context, **response_kwargs)

    def process_check_report(self, report):
        try:
            case_table = []
            summary = []
            solutions = sorted(map(int, report["summary"].keys()))
            id_to_number = dict(map(lambda x: (x["case_id"], x["case_number"]), report["tasks"]))
            cases = sorted(list(set(map(lambda x: x["case_id"], report["tasks"]))), key=lambda x: id_to_number[x])
            for case in cases:
                partial_result = []
                for solution in solutions:
                    partial_result.append(list(
                        filter(lambda x: x.get("case_id") == case and x.get("solution") == solution,
                               report["tasks"]))[0])
                case_table.append(partial_result)
            for solution in solutions:
                summary.append(report["summary"][str(solution)])
            solutions = list(map(lambda id: Program.objects.get(id=id), solutions))
            return {"success": report["success"], "error": report.get("error", ""),
                    "solutions": solutions, "table": case_table, "summary": summary}
        except Exception as e:
            print(e)
            raise ValueError("Illegal report format")

    def process_check_report_detail(self, report, solution_id, case_id):
        ft = list(filter(lambda x: x.get("solution") == solution_id and x.get("case_id") == case_id, report["tasks"]))
        if len(ft) == 0:
            raise Http404
        dt = ft[0]
        # TODO: solution permission check
        solution = Program.objects.get(id=solution_id)
        return [
            ("Source", solution.name),
            ("Language", solution.get_lang_display()),
            ("Test #", dt.get("case_number", "")),
            ("Verdict", dt.get("verdict", "")),
            ("Time", "%d ms" % round(dt.get("time", 0) * 1000)),
            ("Memory", "%d MB" % round(dt.get("memory", 0))),
            ("Exit Code", dt.get("exit_code", 0)),
            ("Signal", dt.get("signal", 0)),
            ("Input", dt.get("input", "")),
            ("Output", dt.get("output", "")),
            ("Answer", dt.get("answer", "")),
            ("Stderr", dt.get("stderr", "")),
            ("Checker's Comment", dt.get("checker_comment", "")),
            ("Checker Exitcode", dt.get("checker_exit_code", "")),
            ("Code", transform_code_to_html(solution.code, solution.lang))
        ]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["task"] = self.revision.task_set.get(id=kwargs["tpk"])
        tags = ("CHECK", "VALIDATE",)
        data["tag"] = "PRETTY"
        for tag in tags:
            if data["task"].abstract.startswith(tag):
                data["tag"] = tag
                break
        print(data["tag"], data["task"].abstract)

        data["disable_grid"] = True
        try:
            data["report"] = json.loads(data["task"].report)
            data["task"].pretty_report = json.dumps(data["report"], indent=2, sort_keys=True)

            if data["tag"] == "CHECK":
                if "detail" in self.request.GET and "solution" in self.request.GET and "case" in self.request.GET:
                    data["tag"] = "CHECK_DETAIL"
                    data["report"] = self.process_check_report_detail(data["report"], int(self.request.GET["solution"]),
                                                                      int(self.request.GET["case"]))
                else:
                    data["report"] = self.process_check_report(data["report"])
            elif data["tag"] == "VALIDATE":
                pass
            
        except json.JSONDecodeError:
            data["report"] = {}
            data["task"].pretty_report = ""
        except ValueError:
            data["tag"] = "PRETTY"

        return data
