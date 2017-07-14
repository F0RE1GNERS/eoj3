from django.shortcuts import render, HttpResponseRedirect, reverse, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.db.models import Q

from django.core.exceptions import PermissionDenied
from tagging.models import Tag, TaggedItem, ContentType
from collections import Counter

from .models import Problem
from .tasks import get_many_problem_accept_count
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
        if tg:
            queryset = TaggedItem.objects.get_by_model(Problem, get_object_or_404(Tag, name=tg))
        else:
            queryset = Problem.objects.all()
        if not is_admin_or_root(self.request.user):
            queryset = queryset.filter(visible=True)

        if kw:
            q = Q(title__icontains=kw) | Q(source__icontains=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw)
            queryset = queryset.filter(q)
            if not self.request.user.is_authenticated or self.request.user.show_tags:
                tag = Tag.objects.filter(name=kw)
                if tag.exists():
                    queryset = (queryset | TaggedItem.objects.get_by_model(Problem, tag.first())).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        data = super(ProblemList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        show_tags = True
        current_problem_set = [problem.pk for problem in data['problem_list']]
        if self.request.user.is_authenticated:
            show_tags = self.request.user.show_tags
            # Get AC / Wrong
            submission_list = self.request.user.submission_set.only('pk', 'author_id', 'problem_id', 'status'). \
                filter(problem_id__in=current_problem_set).all()
            submission_set = dict()
            for submission in submission_list:
                if submission_set.get(submission.problem_id) != 'success':
                    if submission.status != SubmissionStatus.ACCEPTED:
                        submission_set[submission.problem_id] = 'danger'
                    else:
                        submission_set[submission.problem_id] = 'success'
            for problem in data['problem_list']:
                if submission_set.get(problem.pk) is not None:
                    problem.status = submission_set.get(problem.pk)

        # Get Accepted of all users
        accept_count = get_many_problem_accept_count(list(map(lambda x: x.id, data['problem_list'])))
        for problem in data['problem_list']:
            problem.accept_count = accept_count[problem.id]

        # Get tags
        if show_tags:
            tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                                .filter(object_id__in=current_problem_set))
            for problem in data['problem_list']:
                items = list(filter(lambda x: x.object_id == problem.pk, tagged_items))
                if items:
                    problem.my_tags = map(lambda x: x.tag.name, items)

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
        if self.request.user.is_authenticated:
            data['submissions'] = self.problem.submission_set.only("create_time", "pk", "status", "problem_id").\
                                 filter(author=self.request.user).all()[:10]

        show_tags = True
        if self.request.user.is_authenticated:
            show_tags = self.request.user.show_tags
        if show_tags:
            data['tags'] = self.problem.tags

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
