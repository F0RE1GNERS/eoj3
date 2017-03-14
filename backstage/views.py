from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from .forms import ProblemEditForm
from problem.models import Problem


def index(request):
    return render(request, 'backstage/index.html', {'backstage_active': 'home'})


@method_decorator(login_required(), name='dispatch')
class ProblemCreate(CreateView):
    form_class = ProblemEditForm
    template_name = 'backstage/problem_add.html'

    def get_success_url(self):
        return reverse("backstage:problem")

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        instance.save()
        messages.add_message(self.request, messages.SUCCESS, "Problem was successfully added.")
        return HttpResponseRedirect(self.get_success_url())


@method_decorator(login_required(), name='dispatch')
class ProblemUpdate(UpdateView):
    form_class = ProblemEditForm
    queryset = Problem.objects.all()
    template_name = 'backstage/problem_edit.html'

    def get_success_url(self):
        return self.request.path

    def form_valid(self, form):
        messages.add_message(self.request, messages.SUCCESS, "Your changes have been saved.")
        return super(ProblemUpdate, self).form_invalid(form)


@method_decorator(login_required(), name='dispatch')
class ProblemList(ListView):
    template_name = 'backstage/problem.html'
    queryset = Problem.objects.all()
    paginate_by = 5
    context_object_name = 'problem_list'
