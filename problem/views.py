from django.shortcuts import render, HttpResponseRedirect, reverse, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Problem
from submission.forms import SubmitForm
from dispatcher.tasks import DispatcherThread


class ProblemList(ListView):
    template_name = 'problem_list.jinja2'
    queryset = Problem.objects.filter(visible=True).all()
    paginate_by = 50
    context_object_name = 'problem_list'


@method_decorator(login_required, name='post')
class ProblemView(FormView):
    template_name = 'problem.jinja2'
    form_class = SubmitForm

    def get_initial(self):
        return {'lang': 'cpp'}  # TODO

    def get_context_data(self, **kwargs):
        data = super(ProblemView, self).get_context_data()
        data['problem'] = get_object_or_404(Problem, **self.kwargs).get_markdown()
        return data

    def form_valid(self, form):
        problem = get_object_or_404(Problem, **self.kwargs)
        with transaction.atomic():
            submission = form.save(commit=False)
            submission.problem = problem
            submission.author = self.request.user
            submission.code_length = len(submission.code)
            submission.save()
            update_problem = Problem.objects.select_for_update().get(**self.kwargs)
            update_problem.add_submit()
            update_problem.save()
        DispatcherThread(problem.pk, submission.pk).start()
        return HttpResponseRedirect(reverse('submission', args=[submission.pk]))
