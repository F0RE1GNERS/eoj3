from django import forms
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, UpdateView

from polygon.models import CodeforcesPackage
from polygon.package.adapter import CodeforcesPackageAdapter
from polygon.problem2.views.base import PolygonProblemMixin
from problem.models import Problem, SpecialProgram, get_input_path, get_output_path


class ProblemUpdateFromPackage(PolygonProblemMixin, FormView):
  class UpdateForm(forms.Form):
    update_statement = forms.BooleanField(label="用 Package 中的题面覆盖当前题面（无法撤销，谨慎操作！）", required=False)

  form_class = UpdateForm
  template_name = "polygon/problem2/update.jinja2"

  def form_valid(self, form):
    if self.problem.package_id:
      try:
        package = CodeforcesPackage.objects.get(created_by=self.request.user, id=self.problem.package_id,
                                                status=0)
        adapter = CodeforcesPackageAdapter(package, self.problem)
        adapter.update(form.cleaned_data["update_statement"])
      except CodeforcesPackage.DoesNotExist:
        form.add_error(None, "没有找到合法的 Package。")
        return super().form_invalid(form)
      except Exception as e:
        form.add_error(None, "导入错误: {}".format(e))
        return super().form_invalid(form)
    return super().form_valid(form)

  def get_success_url(self):
    return reverse("polygon:problem_review", kwargs={"pk": self.problem.id})


class ProblemCustomizeForm(forms.ModelForm):
  class Meta:
    model = Problem
    fields = ['title', 'package_id',
              'description', 'input', 'output', 'hint']
    widgets = {
      'description': forms.Textarea(attrs={'class': 'markdown'}),
      'input': forms.Textarea(attrs={'class': 'markdown'}),
      'output': forms.Textarea(attrs={'class': 'markdown'}),
      'hint': forms.Textarea(attrs={'class': 'markdown'}),
    }
    help_texts = {
      'package_id': '如果你不想使用 Package 可以留空',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)


class ProblemReview(PolygonProblemMixin, UpdateView):
  template_name = "polygon/problem2/review.jinja2"
  form_class = ProblemCustomizeForm

  def get_object(self, queryset=None):
    return self.problem

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)

    def data_helper(problem, name):
      nonlocal data
      if getattr(problem, name):
        data[name] = SpecialProgram.objects.get(fingerprint=getattr(problem, name))

    def read_file_preview(path):
      with open(path, "rb") as file:
        file.seek(0)
        p = file.read(20)
        try:
          p = p.decode().strip()
          if file.read(1):
            p += "..."
          return p
        except UnicodeDecodeError:
          return p

    data_helper(self.problem, "checker")
    data_helper(self.problem, "validator")

    data["case_list"] = []
    for hash_str in self.problem.case_list:
      data["case_list"].append({"input_preview": read_file_preview(get_input_path(hash_str)),
                                "output_preview": read_file_preview(get_output_path(hash_str)),
                                "sample": hash_str in self.problem.sample_list})
    return data

  def get_success_url(self):
    return reverse("polygon:problem_review", kwargs={"pk": self.problem.id})