import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import HttpResponseRedirect, HttpResponse, reverse, get_object_or_404, redirect
from django.views.generic import TemplateView
from django.views.generic import View
from django.views.generic.list import ListView

from .forms import ProblemEditForm
from dispatcher.tasks import ProblemRejudgeThread
from problem.models import Problem
from submission.models import Submission
from ..base_views import BaseBackstageMixin, BaseUpdateView


class ProblemMeta(BaseBackstageMixin, TemplateView):

    template_name = 'backstage/problem/problem_meta.jinja2'

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(Problem, **kwargs)
        return super(ProblemMeta, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super(ProblemMeta, self).get_context_data(**kwargs)
        data['problem'] = self.problem
        data['admin_list'] = list(
            map(lambda x: x.user, self.problem.problemmanagement_set.filter(permission='a').select_related("user")))
        return data

    def post(self, request, pk):
        upload_permission_dict = set()
        for x in map(int, filter(lambda x: x, request.POST['admin'].split(','))):
            upload_permission_dict.add(x)  # possible rewrite happens here
        for record in self.problem.problemmanagement_set.all():
            if record in upload_permission_dict:
                upload_permission_dict.remove(record)
            else:
                record.delete()
        for key in upload_permission_dict:
            self.problem.problemmanagement_set.create(user_id=key, permission='a')
        return redirect(reverse('backstage:problem_meta', kwargs={'pk': pk}))


class ProblemUpdate(BaseUpdateView):
    form_class = ProblemEditForm
    queryset = Problem.objects.all()
    template_name = 'backstage/problem/problem_edit.jinja2'

    def post_update(self, instance, form):
        instance.tags = form.cleaned_data['tags']


class ProblemList(BaseBackstageMixin, ListView):
    template_name = 'backstage/problem/problem.jinja2'
    queryset = Problem.objects.order_by("-pk").all()
    paginate_by = 100
    context_object_name = 'problem_list'


class ProblemRejudge(BaseBackstageMixin, View):
    def post(self, request):
        try:
            problem = request.POST['problem']
            submissions = [x.pk for x in Submission.objects.filter(problem__pk=problem).all().reverse()]
            ProblemRejudgeThread(submissions).start()
            messages.success(request, 'Rejudge has been sent.')
        except Exception as e:
            print(repr(e))
            messages.error(request, 'Rejudge failed.')
        return HttpResponseRedirect(request.POST['next'])


class ProblemVisibleSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(pk=pk)
            problem.visible = True if not problem.visible else False
            problem.save(update_fields=["visible"])
        return HttpResponse(json.dumps({'result': 'success'}))


class ProblemAccessAdd(BaseBackstageMixin, View):
    def post(self, request, pk):
        problem = get_object_or_404(Problem, pk=pk)
        if not problem.problemmanagement_set.filter(user_id=request.user.pk).exists():
            problem.problemmanagement_set.create(user_id=request.user.pk, permission='a')
        return HttpResponse(json.dumps({'result': 'success'}))