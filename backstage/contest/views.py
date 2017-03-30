import shortuuid

from django.shortcuts import render, HttpResponseRedirect, reverse
from django.contrib import messages
from django.views.generic.list import ListView
from django.views import View
from django.utils import timezone
from django.db import IntegrityError

from .forms import ContestEditForm
from account.models import User
from contest.models import Contest, ContestProblem, ContestInvitation, ContestParticipant
from problem.models import Problem
from contest.tasks import update_contest, add_participant_with_invitation

from ..base_views import BaseCreateView, BaseUpdateView, BaseBackstageMixin


def get_formatted_time():
    return timezone.now().strftime("%Y-%m-%d 00:00")


class ContestManage(BaseBackstageMixin, View):
    template_name = 'backstage/contest/contest_manage.jinja2'

    @staticmethod
    def get_context_data(**kwargs):
        contest = Contest.objects.get(**kwargs)
        contest_problem_list = ContestProblem.objects.filter(contest=contest).all()
        profile = [('Title', contest.title), ('Description', contest.description),
                   ('Rule', contest.get_rule_display()), ('Allowed lang', contest.allowed_lang),
                   ('Start time', contest.start_time), ('End time', contest.end_time),
                   ('Visible', contest.visible), ('Public', contest.public),
                   ('Freeze', contest.freeze), ('Standings public', contest.standings_public)]
        if contest.freeze:
            profile.append(('Freeze time', contest.freeze_time))
        return dict(profile=profile, contest=contest, contest_problem_list=contest_problem_list,
                    invitation_count=contest.contestinvitation_set.count(),
                    participant_count=contest.contestparticipant_set.count())

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))


class ContestCreate(BaseCreateView):
    initial = {'start_time': get_formatted_time(), 'end_time': get_formatted_time()}
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_add.jinja2'

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_create(self, instance):
        super(ContestCreate, self).post_create(instance)
        update_contest(instance)


class ContestProfileUpdate(BaseUpdateView):
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_update(self, instance):
        super(ContestProfileUpdate, self).post_update(instance)
        update_contest(instance)


class ContestList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 20
    context_object_name = 'contest_list'


class ContestProblemCreate(BaseBackstageMixin, View):
    @staticmethod
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

    def post(self, request, contest_pk):
        try:
            problems = [request.POST['problem']]
        except KeyError:
            problems = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['problems'].split('\n'))))
        contest = Contest.objects.get(pk=contest_pk)
        for problem in problems:
            identifier = self.get_next_identifier([x.identifier for x in contest.contestproblem_set.all()])
            try:
                ContestProblem.objects.create(contest=contest, problem=Problem.objects.get(pk=problem),
                                              identifier=identifier)
            except (ValueError, Problem.DoesNotExist):
                messages.error(request, 'There is no such thing as Problem #%s.' % problem)
            except IntegrityError:
                messages.error(request, 'Problem and ID must be unique.')
        update_contest(contest)
        return HttpResponseRedirect(request.POST['next'])


class ContestProblemDelete(BaseBackstageMixin, View):
    def get(self, request, contest_pk, contest_problem_pk):
        contest = Contest.objects.get(pk=contest_pk)
        contest.contestproblem_set.get(pk=contest_problem_pk).delete()
        update_contest(contest)
        messages.success(request, "This problem has been successfully deleted.")
        return HttpResponseRedirect(reverse('backstage:contest_manage', kwargs={'pk': contest_pk}))


class ContestInvitationList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest_invitation.jinja2'
    paginate_by = 50
    context_object_name = 'invitation_list'

    def get_queryset(self):
        return Contest.objects.get(pk=self.kwargs.get('pk')).contestinvitation_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestInvitationList, self).get_context_data(**kwargs)
        data['contest'] = Contest.objects.get(pk=self.kwargs.get('pk'))
        return data


class ContestInvitationCreate(BaseBackstageMixin, View):
    @staticmethod
    def _create(contest, comment):
        while True:
            try:
                ContestInvitation.objects.create(contest=contest, comment=comment,
                                                 code=shortuuid.ShortUUID().random(12))
                break
            except IntegrityError:
                import sys
                print('Invitation code collision just happened', file=sys.stderr)

    def post(self, request, pk):
        try:
            comments = [''] * int(request.POST['number'])
        except KeyError:
            comments = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['list'].split('\n'))))
        contest = Contest.objects.get(pk=pk)
        for comment in comments:
            self._create(contest, comment)
        return HttpResponseRedirect(request.POST['next'])


class ContestInvitationDelete(BaseBackstageMixin, View):
    def get(self, request, pk, invitation_pk):
        contest = Contest.objects.get(pk=pk)
        contest.contestinvitation_set.get(pk=invitation_pk).delete()
        return HttpResponseRedirect(reverse('backstage:contest_invitation', kwargs={'pk': pk}))


class ContestInvitationAssign(BaseBackstageMixin, View):
    def post(self, request, pk, invitation_pk):
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            add_participant_with_invitation(pk, invitation_pk, user)
            messages.success(request,
                             'The user <strong>%s</strong> has been successfully added to the contest.' % username)
        except User.DoesNotExist:
            messages.error(request, 'The user <strong>%s</strong> does not exist. Please check again.' % username)
        except IntegrityError:
            messages.error(request, 'You cannot add one user twice.')
        return HttpResponseRedirect(request.POST['next'])


class ContestParticipantList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest_participant.jinja2'
    paginate_by = 50
    context_object_name = 'participant_list'

    def get_queryset(self):
        return Contest.objects.get(pk=self.kwargs.get('pk')).contestparticipant_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestParticipantList, self).get_context_data(**kwargs)
        data['contest'] = Contest.objects.get(pk=self.kwargs.get('pk'))
        return data


class ContestParticipantCommentUpdate(BaseBackstageMixin, View):
    def post(self, request, pk, participant_pk):
        comment = request.POST.get('comment')
        participant = ContestParticipant.objects.select_for_update().get(pk=participant_pk)
        participant.comment = comment
        participant.save(update_fields=["comment"])
        return HttpResponseRedirect(request.POST['next'])