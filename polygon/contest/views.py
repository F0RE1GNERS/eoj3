import json
import random

import names
import shortuuid
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect, HttpResponse, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from account.models import User, MAGIC_CHOICE
from account.permissions import is_admin_or_root
from contest.models import Contest, ContestInvitation, ContestParticipant, ContestClarification
from contest.statistics import invalidate_contest
from contest.tasks import add_participant_with_invitation
from problem.models import Problem
from problem.statistics import (
    get_problem_accept_count, get_problem_accept_ratio, get_problem_all_count, get_problem_all_user_count,
    get_problem_accept_user_count, get_problem_accept_user_ratio
)
from problem.views import StatusList
from utils.identicon import Identicon
from utils.download import respond_generate_file
from utils.csv_writer import write_csv
from utils.permission import is_contest_manager
from .forms import ContestEditForm
from polygon.rejudge import rejudge_all_submission_on_contest, rejudge_all_submission_on_contest_problem
from polygon.base_views import PolygonBaseMixin


def reorder_contest_problem_identifiers(contest: Contest, orders=None):
    with transaction.atomic():
        problems = list(contest.contestproblem_set.select_for_update().order_by('identifier').all())
        if orders:
            problems.sort(key=lambda x: orders[x.id])
        if len(problems) > 26:
            for index, problem in enumerate(problems, start=1):
                problem.identifier = str(1000 + index)
                problem.save(update_fields=['identifier'])
        else:
            for index, problem in enumerate(problems, start=0):
                problem.identifier = chr(ord('A') + index)
                problem.save(update_fields=['identifier'])


class ContestList(PolygonBaseMixin, ListView):
    template_name = 'polygon/contest/list.jinja2'
    context_object_name = 'contest_list'

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            return Contest.objects.all()
        else:
            return self.request.user.managing_contests.all()


class PolygonContestMixin(TemplateResponseMixin, ContextMixin, PolygonBaseMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('pk'))
        return super(PolygonContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_contest_manager(self.request.user, self.contest):
            return False
        return super(PolygonContestMixin, self).test_func()

    def get_context_data(self, **kwargs):
        data = super(PolygonContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        return data


class ContestEdit(PolygonContestMixin, UpdateView):
    form_class = ContestEditForm
    template_name = 'polygon/contest/edit.jinja2'
    queryset = Contest.objects.all()

    def get_context_data(self, **kwargs):
        data = super(ContestEdit, self).get_context_data(**kwargs)
        data['admin_list'] = self.contest.managers.all()
        return data

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.allowed_lang = ','.join(form.cleaned_data['allowed_lang'])
        instance.save()
        return redirect(self.request.path)


class ContestCreate(PolygonBaseMixin, View):
    def post(self, request, *args, **kwargs):
        contest = Contest.objects.create(title='Contest')
        contest.title = 'Contest #%d' % contest.id
        contest.save(update_fields=['title'])
        contest.managers.add(request.user)
        return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(contest.id)}))


class ContestToggleVisible(PolygonContestMixin, View):
    def post(self, request, pk):
        self.contest.visible = not self.contest.visible
        self.contest.save(update_fields=['visible'])
        return HttpResponse()


class ContestAccessManage(PolygonContestMixin, View):
    def post(self, request, pk):
        upload_permission_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        for record in self.contest.managers.all():
            if record.id in upload_permission_set:
                upload_permission_set.remove(record.id)
            else:
                record.delete()
        for key in upload_permission_set:
            self.contest.managers.add(User.objects.get(pk=key))
        return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))


class ContestProblemManage(PolygonContestMixin, TemplateView):
    template_name = 'polygon/contest/problem.jinja2'

    def get(self, request, *args, **kwargs):
        if 'data' in request.GET:
            problems = self.contest.contestproblem_set.select_related('problem').all()
            data = []
            SUB_FIELDS = ["title", "id", "alias"]
            STATISTIC_FIELDS = [
                ('ac1', get_problem_accept_count),
                ('ac2', get_problem_accept_user_count),
                ('tot1', get_problem_all_count),
                ('tot2', get_problem_all_user_count),
                ('ratio1', get_problem_accept_ratio),
                ('ratio2', get_problem_accept_user_ratio),
            ]
            for problem in problems:
                d = {k: getattr(problem.problem, k) for k in SUB_FIELDS}
                d.update(pid=problem.id, identifier=problem.identifier, weight=problem.weight)
                d.update({k: v(problem.problem_id, self.contest.id) for k, v in STATISTIC_FIELDS})
                data.append(d)
            data.sort(key=lambda x: x['identifier'])
            return HttpResponse(json.dumps(data))
        return super(ContestProblemManage, self).get(request, *args, **kwargs)


class ContestProblemReorder(PolygonContestMixin, View):
    def post(self, request, *args, **kwargs):
        data = {k['pid']: index for (index, k) in enumerate(json.loads(request.POST['orders']))}
        reorder_contest_problem_identifiers(self.contest, data)
        return HttpResponse()


class ContestProblemCreate(PolygonContestMixin, View):
    def post(self, request, pk):
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

        problems = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['problems'].split(','))))
        for problem in problems:
            if not is_admin_or_root(request.user) and not problem.managers.filter(pk=request.user.pk).exists():
                raise PermissionDenied
        for problem in problems:
            if self.contest.contestproblem_set.filter(problem_id=problem).exists():
                continue
            identifier = get_next_identifier([x.identifier for x in self.contest.contestproblem_set.all()])
            self.contest.contestproblem_set.create(problem_id=problem, identifier=identifier)
        reorder_contest_problem_identifiers(self.contest)
        return HttpResponse()


class ContestProblemDelete(PolygonContestMixin, View):
    def post(self, request, pk):
        self.contest.contestproblem_set.filter(id=request.POST['pid']).delete()
        reorder_contest_problem_identifiers(self.contest)
        return HttpResponse()


class ContestProblemChangeWeight(PolygonContestMixin, View):
    def post(self, request, pk):
        problem = self.contest.contestproblem_set.get(id=request.POST['pid'])
        problem.weight = int(request.POST['weight'])
        assert 0 < problem.weight <= 10000
        problem.save(update_fields=['weight'])
        return HttpResponse()


class ContestInvitationList(PolygonContestMixin, ListView):
    template_name = 'polygon/contest/invitation.jinja2'
    paginate_by = 100
    context_object_name = 'invitation_list'

    def get_queryset(self):
        return Contest.objects.get(pk=self.kwargs.get('pk')).contestinvitation_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestInvitationList, self).get_context_data(**kwargs)
        data['contest'] = Contest.objects.get(pk=self.kwargs.get('pk'))
        return data


class ContestInvitationCreate(PolygonContestMixin, View):
    @staticmethod
    def _create(contest, comments):
        random_gen = shortuuid.ShortUUID()
        ContestInvitation.objects.bulk_create(
            [ContestInvitation(contest=contest, code=random_gen.random(12), comment=comment) for comment in comments])

    def post(self, request, pk):
        try:
            comments = [''] * int(request.POST['number'])
        except KeyError:
            comments = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['list'].split('\n'))))
        contest = Contest.objects.get(pk=pk)
        self._create(contest, comments)
        return HttpResponseRedirect(request.POST['next'])


class ContestInvitationDelete(PolygonContestMixin, View):
    def post(self, request, pk, invitation_pk):
        contest = Contest.objects.get(pk=pk)
        contest.contestinvitation_set.get(pk=invitation_pk).delete()
        return HttpResponseRedirect(request.url)


class ContestInvitationAssign(PolygonContestMixin, View):
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


class ContestParticipantList(PolygonContestMixin, ListView):
    template_name = 'polygon/contest/participant.jinja2'
    paginate_by = 100
    context_object_name = 'participant_list'

    def get_queryset(self):
        return Contest.objects.get(pk=self.kwargs.get('pk')).contestparticipant_set.all()

    def get_context_data(self, **kwargs):
        data = super(ContestParticipantList, self).get_context_data(**kwargs)
        data['contest'] = Contest.objects.get(pk=self.kwargs.get('pk'))
        return data


class ContestParticipantCommentUpdate(PolygonContestMixin, View):
    def post(self, request, pk, participant_pk):
        comment = request.POST.get('comment')
        with transaction.atomic():
            participant = ContestParticipant.objects.select_for_update().get(pk=participant_pk)
            participant.comment = comment
            participant.save(update_fields=["comment"])
        return HttpResponseRedirect(request.POST['next'])


class ContestParticipantStarToggle(PolygonContestMixin, View):
    def post(self, request, pk, participant_pk):
        with transaction.atomic():
            participant = Contest.objects.get(pk=pk).contestparticipant_set.select_for_update().get(pk=participant_pk)
            participant.star = True if not participant.star else False
            participant.save(update_fields=["star"])
        return HttpResponse()


class ContestParticipantCreate(PolygonContestMixin, View):
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
        invalidate_contest(contest)
        return HttpResponseRedirect(request.POST['next'])


class ContestClarificationAnswer(PolygonContestMixin, View):
    def post(self, request, pk, clarification_id):
        clarification = ContestClarification.objects.get(pk=clarification_id)
        clarification.answer = request.POST['answer']
        clarification.save(update_fields=["status", "answer"])
        return HttpResponseRedirect(reverse('contest:clarification', kwargs={'cid': pk}))


class RejudgeContestProblemSubmission(PolygonContestMixin, View):
    def post(self, request, pk):
        my_problem = request.POST['problem']
        if my_problem == 'all':
            rejudge_all_submission_on_contest(self.contest)
        else:
            rejudge_all_submission_on_contest_problem(self.contest, get_object_or_404(Problem, pk=my_problem))
        return redirect(reverse('polygon:contest_status', kwargs={'pk': self.contest.id}))


class ContestStatusBackend(PolygonContestMixin, StatusList):

    template_name = 'polygon/contest/status.jinja2'
    contest_submission_visible = True

    def get_selected_from(self):
        return self.contest.submission_set.all()

    def reinterpret_problem_identifier(self, value):
        return self.contest.contestproblem_set.get(identifier=value).problem_id

    def get_context_data(self, **kwargs):
        data = super(ContestStatusBackend, self).get_context_data(**kwargs)
        self.contest.add_contest_problem_to_submissions(data['submission_list'])
        return data


class ContestInvitationCodeDownload(PolygonContestMixin, View):

    def get(self, request, pk):
        data = [[user.comment, user.code] for user in self.contest.contestinvitation_set.all()]
        filename = write_csv(data)
        return respond_generate_file(request, filename, file_name_serve_as="InvitationCode - %s.csv" % self.contest.title)


class ContestParticipantsNoteDownload(PolygonContestMixin, View):

    def get(self, request, pk):
        data = [[user.comment, user.user.username, user.hidden_comment] for user in
                self.contest.contestparticipant_set.select_related("user").all()]
        filename = write_csv(data)
        return respond_generate_file(request, filename, file_name_serve_as="ContestParticipant - %s.csv" % self.contest.title)


class ContestAccountDisable(PolygonContestMixin, View):
    def post(self, request, pk, participant_pk):
        contest_participant = get_object_or_404(ContestParticipant, pk=participant_pk)
        contest_participant.is_disabled = not contest_participant.is_disabled
        contest_participant.save(update_fields=['is_disabled'])
        return JsonResponse({})