import re

from django import forms
from tagging.models import Tag

from polygon.models import Statement, Revision, Program, Case, Asset, Template
from problem.models import Problem, SpecialProgram
from utils.multiple_choice_field import CommaSeparatedMultipleChoiceField


class ProblemEditForm(forms.ModelForm):
  class Meta:
    model = Problem
    fields = ['title', 'alias', 'time_limit', 'memory_limit', 'description', 'input', 'output',
              'hint', 'source']
    error_messages = {
    }
    widgets = {
      'description': forms.Textarea(attrs={'class': 'markdown'}),
      'input': forms.Textarea(attrs={'class': 'markdown'}),
      'output': forms.Textarea(attrs={'class': 'markdown'}),
      'hint': forms.Textarea(attrs={'class': 'markdown'}),
    }

  tags = CommaSeparatedMultipleChoiceField(required=False)

  def __init__(self, *args, **kwargs):
    super(ProblemEditForm, self).__init__(*args, **kwargs)
    new_order = ['title', 'alias', 'time_limit', 'memory_limit', 'description',
                 'input', 'output', 'hint', 'tags', 'source']
    self.fields = type(self.fields)((k, self.fields[k]) for k in new_order)
    if self.instance:
      self.fields['tags'].initial = ','.join(map(str, self.instance.tags))
      self.fields['tags'].choices = [(i, i) for i in Tag.objects.all()]

  def clean(self):
    cleaned_data = super().clean()
    used_tag = []
    if 'tags' in cleaned_data:
      for tag in cleaned_data['tags']:
        if Tag.objects.filter(name=tag).exists():
          used_tag.append(tag)
    cleaned_data['tags'] = ', '.join(used_tag)
    if ',' not in cleaned_data['tags']:
      cleaned_data['tags'] = "\"%s\"" % cleaned_data['tags']
    return cleaned_data


class RevisionUpdateForm(forms.ModelForm):
  class Meta:
    model = Revision
    fields = ['time_limit', 'memory_limit', 'well_form_policy', 'enable_group', 'group_count',
              'group_dependencies', 'group_points']
    widgets = {
      "group_dependencies": forms.TextInput(),
      "group_points": forms.TextInput(),
    }

  def clean_group_dependencies(self):
    self.group_dependency_list = []
    data = self.cleaned_data["group_dependencies"]
    if not data.strip():
      return ""
    try:
      p = list(filter(lambda x: x, data.strip().split(";")))
      for t in p:
        u, v = map(int, t.strip().split(","))
        if u <= v:
          raise forms.ValidationError("Edge must follow topological order.")
        self.group_dependency_list.append((u, v))
    except (TypeError, ValueError):
      raise forms.ValidationError("Please write the dependencies in forms of 1,2;2,3;3,4 or similar, "
                                  "or left empty if you don't want to use this feature.")
    return ";".join(map(lambda x: str(x[0]) + "," + str(x[1]), self.group_dependency_list))

  def clean_group_points(self):
    self.group_point_list = []
    data = self.cleaned_data["group_points"]
    if not data.strip():
      return ""
    try:
      p = list(filter(lambda x: x, re.split(r'[;, ]+', data)))
      self.group_point_list = list(map(lambda x: int(x.strip()), p))
    except (TypeError, ValueError):
      raise forms.ValidationError("Please write the group points in forms of 10,20,30,10 or similar, "
                                  "or left empty if you don't want to use this feature.")
    return ",".join(map(str, self.group_point_list))

  def clean_group_count(self):
    self.group_count = self.cleaned_data["group_count"]
    if self.group_count < 1 or self.group_count > 10:
      raise forms.ValidationError("Group count should not be lower than 1 or greater than 10.")
    return self.group_count

  def clean(self):
    if self.cleaned_data["enable_group"]:
      if not all([1 <= y <= self.group_count for x in self.group_dependency_list for y in x]):
        raise forms.ValidationError("Illegal group not in range of 1 to group count.")
      if len(self.group_point_list) != self.group_count:
        raise forms.ValidationError("Illegal group points configuration does not match the group count.")
    return self.cleaned_data


class StatementUpdateForm(forms.ModelForm):
  class Meta:
    model = Statement
    exclude = ['create_time', 'update_time', 'activated', 'parent_id']
    widgets = {
      'description': forms.Textarea(attrs={'class': 'markdown'}),
      'input': forms.Textarea(attrs={'class': 'markdown'}),
      'output': forms.Textarea(attrs={'class': 'markdown'}),
      'hint': forms.Textarea(attrs={'class': 'markdown'}),
    }


class ProgramUpdateForm(forms.ModelForm):
  class Meta:
    model = Program
    fields = ["name", "lang", "code", "tag"]


class ProgramImportForm(forms.Form):
  program = forms.ChoiceField()

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    program_choices = []
    for program in SpecialProgram.objects.filter(builtin=True).order_by("category", "filename"):
      program_choices.append((program.fingerprint, "%s - %s" % (program.get_category_display(), program.filename)))
    self.fields["program"].choices = program_choices


class CaseCreateForm(forms.Form):
  option = forms.ChoiceField(choices=(
    ('text', '手填输入输出'),
    ('batch', '上传含输入输出文件的压缩包')))
  input_text = forms.CharField(required=False, widget=forms.Textarea())
  output_text = forms.CharField(required=False, widget=forms.Textarea())
  batch_file = forms.FileField(required=False)
  in_samples = forms.BooleanField(initial=False, required=False)
  case_number = forms.IntegerField(initial=0)
  activated = forms.BooleanField(initial=True, required=False)

  def clean(self):
    if self.cleaned_data["option"] == "single" and (
        self.cleaned_data["input_file"] is None or self.cleaned_data["output_file"] is None):
      raise forms.ValidationError("输入输出文件是必须的。")
    if self.cleaned_data["option"] == "batch" and self.cleaned_data["batch_file"] is None:
      raise forms.ValidationError("文件压缩包是必须的。")


class CaseUpdateInfoForm(forms.ModelForm):
  class Meta:
    model = Case
    fields = ["in_samples", "activated", "points", "description", "case_number", "group"]
    labels = {
      "activated": "是有效的测试点",
    }


class CaseUpdateForm(forms.Form):
  input_text = forms.CharField(widget=forms.Textarea(), required=False)
  output_text = forms.CharField(widget=forms.Textarea(), required=False)


class AssetRenameForm(forms.ModelForm):
  class Meta:
    model = Asset
    fields = ["name"]


class AssetUpdateForm(forms.ModelForm):
  class Meta:
    model = Asset
    fields = ["name", "file"]


class TemplateUpdateForm(forms.ModelForm):
  class Meta:
    model = Template
    fields = ["language", "template_code", "grader_code"]
