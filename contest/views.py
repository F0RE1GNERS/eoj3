from django.shortcuts import render
from django.views.generic.list import ListView
from .models import Contest


class ContestList(ListView):
    template_name = 'contest_list.html'
    queryset = Contest.objects.filter(visible=True).all()
    paginate_by = 50
    context_object_name = 'contest_list'


def dashboard(request, pk):
    return render(request, 'contest/base.html')
