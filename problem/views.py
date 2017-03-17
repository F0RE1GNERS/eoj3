from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views import View
from django.db import transaction

from .models import Problem
from submission.forms import SubmitForm
from dispatcher.tasks import DispatcherThread
from utils import markdown3


class ProblemList(ListView):
    template_name = 'problem_list.html'
    queryset = Problem.objects.filter(visible=True).all()
    paginate_by = 50
    context_object_name = 'problem_list'


def problem_view(request, problem_id):
    form = SubmitForm(initial={'lang': 'cpp'})  # TODO
    return render(request, 'problem.html', {'form': form})


class ProblemView(View):
    template_name = 'problem.html'
    form_class = SubmitForm

    def post(self, request, **kwargs):
        problem = Problem.objects.get(**kwargs)
        form = self.form_class(request.POST)
        if form.is_valid():
            with transaction.atomic():
                submission = form.save(commit=False)
                submission.problem = problem
                submission.author = request.user
                submission.code_length = len(submission.code)
                submission.save()
                update_problem = Problem.object.select_for_update().get(**kwargs)
                update_problem.add_submit()
                update_problem.save()
            DispatcherThread(problem.pk, submission.pk).start()
            return HttpResponseRedirect(reverse('submission', args=[submission.pk]))
        else:
            body = markdown3.convert(problem.description)
            data = dict(problem=problem, form=form, body=body)
            return render(request, self.template_name, data)

    def get(self, request, **kwargs):
        problem = Problem.objects.get(**kwargs)
        form = self.form_class()
        body = markdown3.convert(problem.description)
        data = dict(problem=problem, form=form, body=body)
        return render(request, self.template_name, data)
