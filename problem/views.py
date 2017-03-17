from django.shortcuts import render, HttpResponseRedirect, reverse, get_object_or_404
from django.views.generic.list import ListView
from django.views import View

from .models import Problem
from submission.forms import SubmitForm
from dispatcher.tasks import DispatcherThread


class ProblemList(ListView):
    template_name = 'problem_list.html'
    queryset = Problem.objects.filter(visible=True).all()
    paginate_by = 50
    context_object_name = 'problem_list'


class ProblemView(View):
    template_name = 'problem.html'
    form_class = SubmitForm
    form_initial = {'lang': 'cpp'}  # TODO

    def post(self, request, **kwargs):
        problem = get_object_or_404(Problem, **kwargs)
        form = self.form_class(request.POST, initial=self.form_initial)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.problem = problem
            submission.author = request.user
            submission.code_length = len(submission.code)
            problem.total_submit_number += 1
            submission.save()
            problem.save()
            DispatcherThread(problem.pk, submission.pk).start()
            return HttpResponseRedirect(reverse('submission', args=[submission.pk]))
        else:
            data = dict(problem=problem.get_markdown(), form=form)
            return render(request, self.template_name, data)

    def get(self, request, **kwargs):
        problem = get_object_or_404(Problem, **kwargs).get_markdown()
        form = self.form_class(initial=self.form_initial)
        data = dict(problem=problem, form=form)
        return render(request, self.template_name, data)
