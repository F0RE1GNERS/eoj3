from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Contest
from .views import BaseContestMixin, time_formatter, get_contest_problem
from submission.models import Submission, SubmissionStatus
from submission.forms import ContestSubmitForm
from dispatcher.tasks import submit_code_for_contest


class ContestSubmit(BaseContestMixin, FormView):
    template_name = 'contest/submit.jinja2'
    form_class = ContestSubmitForm

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('cid'))
        self.contest_allowed_lang = self.get_allowed_lang(self.contest)
        return super(ContestSubmit, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get_allowed_lang(contest):
        return sorted(list(filter(lambda x: x, map(lambda x: x.strip(), contest.allowed_lang.split(',')))))

    def get_initial(self):
        res = {'problem_identifier': self.request.GET.get('pid', '')}
        if self.user.is_authenticated and self.user.preferred_lang in self.contest_allowed_lang:
            res['lang'] = self.user.preferred_lang
        return res

    def get_form_kwargs(self):
        kwargs = super(ContestSubmit, self).get_form_kwargs()
        kwargs['contest_problem_list'] = self.contest_problem_list
        kwargs['contest_allowed_lang'] = self.contest_allowed_lang
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Please login first.')

        if self.contest.get_status() != 'running':
            messages.error(self.request, 'You are currently not in the period of the contest.')
            return HttpResponseRedirect(self.request.path)

        submission = form.save(commit=False)
        if not submission.lang in self.contest_allowed_lang:
            messages.error(self.request, '%s is not supported.' % submission.lang)
            return HttpResponseRedirect(self.request.path)

        problem_identifier = form.cleaned_data['problem_identifier']
        submit_code_for_contest(submission, self.user, problem_identifier, self.contest)
        return HttpResponseRedirect(reverse('contest:submission', kwargs={'cid': self.kwargs['cid']}))


class ContestMySubmission(BaseContestMixin, ListView):
    template_name = 'contest/submission.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        if not self.user.is_authenticated:
            raise PermissionDenied('Please login first.')
        return self.contest.submission_set.filter(author=self.user).all()

    def get_context_data(self, **kwargs):
        data = super(ContestMySubmission, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - self.contest.start_time).seconds)
            submission.contest_problem = get_contest_problem(self.contest_problem_list, submission.problem_id)
        return data


class ContestStatus(BaseContestMixin, ListView):
    template_name = 'contest/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        contest = Contest.objects.get(pk=self.kwargs.get('cid'))
        if self.privileged or contest.get_frozen == 'a':
            return Submission.objects.filter(contest=contest).all()
        elif contest.get_frozen() == 'f2':
            return Submission.objects.none()
        else:
            return Submission.objects.filter(contest=contest, create_time__lt=contest.freeze_time).all()

    def get_context_data(self, **kwargs):
        data = super(ContestStatus, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - self.contest.start_time).seconds)
            submission.contest_problem = get_contest_problem(self.contest_problem_list, submission.problem_id)
        return data