import shortuuid

from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.views import View
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import IntegrityError

from .forms import ContestEditForm
from contest.models import Contest, ContestProblem, ContestInvitation
from problem.models import Problem
from group.models import Group
from contest.tasks import update_contest
from utils import markdown3

from ..base_views import BaseCreateView, BaseUpdateView


def get_formatted_time():
    return timezone.now().strftime("%Y-%m-%d 00:00")


class ContestManage(View):
    template_name = 'backstage/contest/contest_manage.html'

    @staticmethod
    def get_context_data(**kwargs):
        contest = Contest.objects.get(**kwargs)
        contest_problem_list = ContestProblem.objects.filter(contest=contest).all()
        profile = [('Title', contest.title), ('Description', contest.description),
                   ('Rule', contest.get_rule_display()), ('Start time', contest.start_time),
                   ('End time', contest.end_time), ('Visible', contest.visible), ('Public', contest.public)]
        return dict(profile=profile, contest=contest, contest_problem_list=contest_problem_list)

    def post(self, request, **kwargs):
        group_pk = request.POST.get('group')
        contest = Contest.objects.get(**kwargs)
        if group_pk:
            contest.groups.add(Group.objects.get(pk=group_pk))
        update_contest(contest)
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))


class ContestCreate(BaseCreateView):
    initial = {'start_time': get_formatted_time(), 'end_time': get_formatted_time()}
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_add.html'

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_create(self, instance):
        super(ContestCreate, self).post_create(instance)
        update_contest(instance)


class ContestProfileUpdate(BaseUpdateView):
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_edit.html'
    queryset = Contest.objects.all()

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_update(self, instance):
        super(ContestProfileUpdate, self).post_update(instance)
        update_contest(instance)


@method_decorator(login_required(), name='dispatch')
class ContestList(ListView):
    template_name = 'backstage/contest/contest.html'
    queryset = Contest.objects.all()
    paginate_by = 20
    context_object_name = 'contest_list'


def contest_problem_create(request, contest_pk):

    def get_next_identifier(identifiers):
        from collections import deque
        q = deque()
        q.append('')
        while q:
            u = q.popleft()
            if u and u not in identifiers:
                return u
            for i in range(ord('A'), ord('Z') + 1):
                q.append(u + chr(i))

    if request.method == 'POST':
        try:
            problems = [request.POST['problem']]
        except KeyError:
            problems = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['problems'].split('\n'))))
        contest = Contest.objects.get(pk=contest_pk)
        for problem in problems:
            identifier = get_next_identifier([x.identifier for x in contest.contestproblem_set.all()])
            try:
                ContestProblem.objects.create(contest=contest, problem=Problem.objects.get(pk=problem),
                                              identifier=identifier)
            except (ValueError, Problem.DoesNotExist):
                messages.error(request, 'There is no such thing as Problem #%s.' % problem)
            except IntegrityError:
                messages.error(request, 'Problem and ID must be unique.')
        update_contest(contest)
        return HttpResponseRedirect(request.POST['next'])


def contest_problem_delete(request, contest_pk, contest_problem_pk):
    contest = Contest.objects.get(pk=contest_pk)
    contest.contestproblem_set.get(pk=contest_problem_pk).delete()
    update_contest(contest)
    messages.success(request, "This problem has been successfully deleted.")
    return HttpResponseRedirect(reverse('backstage:contest_manage', kwargs={'pk': contest_pk}))


class ContestInvitationList(ListView):
    template_name = 'backstage/contest/contest_invitation.html'
    paginate_by = 50
    context_object_name = 'invitation_list'

    def get_queryset(self):
        print(Contest.objects.get(pk=self.kwargs.get('pk')))
        print(Contest.objects.get(pk=self.kwargs.get('pk')).contestinvitation_set.all())
        print(Contest.objects.get(pk=self.kwargs.get('pk')).contestinvitation_set.all())
        return Contest.objects.get(pk=self.kwargs.get('pk')).contestinvitation_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestInvitationList, self).get_context_data(**kwargs)
        data['contest'] = Contest.objects.get(pk=self.kwargs.get('pk'))
        return data


def contest_invitation_create(request, pk):

    def _create(contest, comment):
        while True:
            try:
                ContestInvitation.objects.create(contest=contest, comment=comment,
                                                 code=shortuuid.ShortUUID().random(12))
                break
            except IntegrityError:
                import sys
                print('Invitation code collision just happened', file=sys.stderr)

    if request.method == 'POST':
        try:
            comments = [''] * int(request.POST['number'])
        except KeyError:
            comments = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['list'].split('\n'))))
        contest = Contest.objects.get(pk=pk)
        for comment in comments:
            _create(contest, comment)
        return HttpResponseRedirect(request.POST['next'])
