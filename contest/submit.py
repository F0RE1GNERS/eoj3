from django.shortcuts import render, get_object_or_404, get_list_or_404, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic.edit import FormView
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import Contest
from .views import BaseContestMixin, time_formatter, get_contest_problem
from submission.models import Submission, SubmissionStatus
from submission.forms import ContestSubmitForm
from dispatcher.tasks import submit_code_for_contest
from account.permissions import is_admin_or_root


class ContestSubmit(BaseContestMixin, FormView):
    template_name = 'contest/submit.jinja2'
    form_class = ContestSubmitForm

    @staticmethod
    def get_allowed_lang(contest):
        return sorted(list(filter(lambda x: x, map(lambda x: x.strip(), contest.allowed_lang.split(',')))))

    def get_initial(self):
        res = {'problem_identifier': self.request.GET.get('pid', '')}
        if self.request.user.is_authenticated and self.request.user.preferred_lang in \
            self.get_allowed_lang(Contest.objects.get(pk=self.kwargs['cid'])):
            res.update({'lang': self.request.user.preferred_lang})
        return res

    def get_form_kwargs(self):
        kwargs = super(ContestSubmit, self).get_form_kwargs()
        contest = Contest.objects.get(pk=self.kwargs['cid'])
        kwargs['contest_problem_list'] = contest.contestproblem_set.all()
        kwargs['contest_allowed_lang'] = self.get_allowed_lang(contest)
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Please login first.')
        contest = get_object_or_404(Contest, pk=self.kwargs['cid'])

        if timezone.now() < contest.start_time or timezone.now() > contest.end_time:
            messages.error(self.request, 'You are currently not in the period of the contest.')
            return HttpResponseRedirect(self.request.path)

        submission = form.save(commit=False)
        if not submission.lang in self.get_allowed_lang(contest):
            messages.error(self.request, '%s is not supported.' % submission.lang)
            return HttpResponseRedirect(self.request.path)

        problem_identifier = form.cleaned_data['problem_identifier']
        submit_code_for_contest(submission, self.request.user, problem_identifier, contest)
        return HttpResponseRedirect(reverse('contest:submission', kwargs={'cid': self.kwargs['cid']}))


class ContestMySubmission(BaseContestMixin, ListView):
    template_name = 'contest/submission.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Please login first.')
        return Submission.objects.filter(contest=Contest.objects.get(pk=self.kwargs.get('cid')),
                                         author=self.request.user).all()

    def get_context_data(self, **kwargs):
        data = super(ContestMySubmission, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - data['contest'].start_time).seconds)
            submission.contest_problem = get_contest_problem(data['contest'], submission.problem)
        return data


class ContestStatus(BaseContestMixin, ListView):
    template_name = 'contest/status.jinja2'
    paginate_by = 50
    context_object_name = 'submission_list'

    def get_queryset(self):
        contest = Contest.objects.get(pk=self.kwargs.get('cid'))
        if is_admin_or_root(self.request.user):
            return Submission.objects.filter(contest=contest).all()
        elif contest.get_frozen() != 'available':
            return Submission.objects.none()
        elif contest.freeze and contest.get_status() == 'running':
            return Submission.objects.filter(contest=contest, create_time__lt=contest.freeze_time).all()
        else:
            return Submission.objects.filter(contest=contest).all()

    def get_context_data(self, **kwargs):
        data = super(ContestStatus, self).get_context_data(**kwargs)
        for submission in data['submission_list']:
            submission.create_time = time_formatter((submission.create_time - data['contest'].start_time).seconds)
            submission.contest_problem = get_contest_problem(data['contest'], submission.problem)
        return data