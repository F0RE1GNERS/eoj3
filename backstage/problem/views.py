from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from .forms import ProblemEditForm
from problem.models import Problem

from ..base_views import BaseCreateView, BaseUpdateView


def index(request):
    return render(request, 'backstage/index.html')


class ProblemCreate(BaseCreateView):
    form_class = ProblemEditForm
    template_name = 'backstage/problem/problem_add.html'

    def get_redirect_url(self, instance):
        return reverse("backstage:problem")


class ProblemUpdate(BaseUpdateView):
    form_class = ProblemEditForm
    queryset = Problem.objects.all()
    template_name = 'backstage/problem/problem_edit.html'


@method_decorator(login_required(), name='dispatch')
class ProblemList(ListView):
    template_name = 'backstage/problem/problem.html'
    queryset = Problem.objects.all()
    paginate_by = 5
    context_object_name = 'problem_list'
