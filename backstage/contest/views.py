import shortuuid
import json
import names
import random

from django.shortcuts import render, HttpResponseRedirect, HttpResponse, reverse
from django.views import static, View
from django.views.generic import TemplateView
from django.contrib import messages
from django.views.generic.list import ListView
from django.utils import timezone
from django.db import IntegrityError, transaction

from eoj3.settings import GENERATE_DIR
from .forms import ContestEditForm
from account.models import User, MAGIC_CHOICE
from contest.models import Contest, ContestProblem, ContestInvitation, ContestParticipant
from problem.models import Problem
from contest.tasks import update_contest, add_participant_with_invitation
from utils import xlsx_generator
from utils.identicon import Identicon
from ..base_views import BaseCreateView, BaseUpdateView, BaseBackstageMixin


def get_formatted_time():
    return timezone.now().strftime("%Y-%m-%d 00:00")


class ContestManage(BaseBackstageMixin, TemplateView):
    template_name = 'backstage/contest/contest_manage.jinja2'

    def get_context_data(self, **kwargs):
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


class ContestCreate(BaseCreateView):
    initial = {'start_time': get_formatted_time(), 'end_time': get_formatted_time()}
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_add.jinja2'

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_create(self, instance, form):
        update_contest(instance)


class ContestProfileUpdate(BaseUpdateView):
    form_class = ContestEditForm
    template_name = 'backstage/contest/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def get_redirect_url(self, instance):
        return reverse('backstage:contest_manage', kwargs={'pk': instance.pk})

    def post_update(self, instance, form):
        update_contest(instance)


class ContestList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 100
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
    def post(self, request, contest_pk, contest_problem_pk):
        contest = Contest.objects.get(pk=contest_pk)
        contest.contestproblem_set.get(pk=contest_problem_pk).delete()
        update_contest(contest)
        messages.success(request, "This problem has been successfully deleted.")
        return HttpResponseRedirect(reverse('backstage:contest_manage', kwargs={'pk': contest_pk}))


class ContestInvitationList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest_invitation.jinja2'
    paginate_by = 100
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
    def post(self, request, pk, invitation_pk):
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
    paginate_by = 100
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
        with transaction.atomic():
            participant = ContestParticipant.objects.select_for_update().get(pk=participant_pk)
            participant.comment = comment
            participant.save(update_fields=["comment"])
        return HttpResponseRedirect(request.POST['next'])


class ContestParticipantStarToggle(BaseBackstageMixin, View):
    def post(self, request, pk, participant_pk):
        with transaction.atomic():
            participant = Contest.objects.get(pk=pk).contestparticipant_set.select_for_update().get(pk=participant_pk)
            participant.star = True if not participant.star else False
            participant.save(update_fields=["star"])
        return HttpResponse(json.dumps({'result': 'success'}))


class ContestParticipantCreate(BaseBackstageMixin, View):

    @staticmethod
    def _get_username(contest_id, user_id):
        return "c%s#%04d" % (str(contest_id), int(user_id))

    def post(self, request, pk):
        namelist = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['list'].split('\n'))))
        user_id = 1
        contest = Contest.objects.get(pk=pk)
        for name in namelist:
            if name.startswith('*'):
                comment = name[1:].strip()
                star = True
            else:
                comment = name
                star = False
            password_gen = shortuuid.ShortUUID("23456789ABCDEF")
            password = password_gen.random(8)
            nickname = names.get_full_name()
            while True:
                try:
                    username = self._get_username(pk, user_id)
                    email = '%s@fake.ecnu.edu.cn' % username
                    user = User.objects.create(username=username, email=email, nickname=nickname,
                                               magic=random.choice(list(dict(MAGIC_CHOICE).keys())))
                    user.set_password(password)
                    user.save()
                    user.avatar.save('generated.png', Identicon(user.email).get_bytes())
                    ContestParticipant.objects.create(user=user, comment=comment, hidden_comment=password,
                                                      star=star, contest=contest)
                    break
                except IntegrityError:
                    pass
                user_id += 1
        update_contest(contest)
        return HttpResponseRedirect(request.POST['next'])


class ContestParticipantDownload(BaseBackstageMixin, View):
    def get(self, request, pk):
        file_name = xlsx_generator.generate_participant(pk)
        return static.serve(request, file_name, document_root=GENERATE_DIR)


class ContestInvitationDownload(BaseBackstageMixin, View):
    def get(self, request, pk):
        file_name = xlsx_generator.generate_invitation(pk)
        return static.serve(request, file_name, document_root=GENERATE_DIR)
