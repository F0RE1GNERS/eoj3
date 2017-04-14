from django.shortcuts import render, HttpResponseRedirect, reverse, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http.response import Http404
from django.core.exceptions import PermissionDenied
from tagging.models import Tag, TaggedItem

from .models import Problem
from submission.forms import SubmitForm
from submission.models import Submission, SubmissionStatus
from dispatcher.tasks import submit_code
from account.permissions import is_admin_or_root
from utils.authentication import test_site_open


class ProblemList(ListView):
    template_name = 'problem_list.jinja2'
    paginate_by = 100
    context_object_name = 'problem_list'

    def get_queryset(self):
        kw = self.request.GET.get('keyword')
        tg = self.request.GET.get('tag')
        if is_admin_or_root(self.request.user):
            queryset = Problem.objects.filter()
        else:
            queryset = Problem.objects.filter(visible=True)
        if tg:
            tag = Tag.objects.filter(name=tg)
            if tag.exists():
                queryset = TaggedItem.objects.get_by_model(Problem, tag.first()).distinct()
        if kw:
            q = Q(title__icontains=kw) | Q(source__icontains=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw)
            queryset = queryset.filter(q)
            if not self.request.user.is_authenticated or self.request.user.show_tags:
                tag = Tag.objects.filter(name=kw)
                if tag.exists():
                    queryset = (queryset | TaggedItem.objects.get_by_model(Problem, tag.first())).distinct()
        return queryset.all()

    def get_context_data(self, **kwargs):
        data = super(ProblemList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        data['show_tags'] = True
        if self.request.user.is_authenticated:
            # Get AC / Wrong
            for problem in data['problem_list']:
                queryset = problem.submission_set.filter(author=self.request.user)
                if queryset.exists():
                    problem.status = 'danger'
                if queryset.filter(status=SubmissionStatus.ACCEPTED).exists():
                    problem.status = 'success'
            # Get tags
            data['show_tags'] = self.request.user.show_tags

        return data


class ProblemView(FormView):
    template_name = 'problem.jinja2'
    form_class = SubmitForm

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(Problem, **kwargs)
        return super(ProblemView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        if self.request.user.is_authenticated:
            return {'lang': self.request.user.preferred_lang}
        return {'lang': 'cpp'}

    def get_context_data(self, **kwargs):
        data = super(ProblemView, self).get_context_data()
        if not is_admin_or_root(self.request.user) and not self.problem.visible:
            raise PermissionDenied("You don't have the access.")
        data['problem'] = self.problem.get_markdown()
        return data

    def form_valid(self, form):
        if not test_site_open(self.request):
            raise PermissionDenied("Site is closed now.")
        if (not self.problem.visible and not is_admin_or_root(self.request.user)) or \
                not self.request.user.is_authenticated:
            raise PermissionDenied("You don't have the access.")
        submission = form.save(commit=False)
        submit_code(submission, self.request.user, self.kwargs.get('pk'))
        return HttpResponseRedirect(reverse('submission', args=[submission.pk]))
