import json
import re
from datetime import timedelta
from os import path
from threading import Thread

import shortuuid
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect, HttpResponse, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.edit import UpdateView, FormView
from django.views.generic.list import ListView

from account.models import User
from account.permissions import is_admin_or_root
from contest.models import Contest, ContestInvitation, ContestParticipant, ContestClarification, Activity
from contest.statistics import invalidate_contest
from contest.tasks import add_participant_with_invitation
from polygon.base_views import PolygonBaseMixin
from polygon.rejudge import rejudge_all_submission_on_contest, rejudge_all_submission_on_contest_problem, \
  rejudge_submission_set
from problem.models import Problem
from problem.views import StatusList
from submission.util import SubmissionStatus
from utils.csv_writer import write_csv
from utils.download import respond_generate_file
from utils.identicon import Identicon
from utils.permission import is_contest_manager
from .forms import ContestEditForm, TestSysUploadForm


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
    data['author_list'] = self.contest.authors.all()
    data['volunteer_list'] = self.contest.volunteers.all()
    return data

  def form_valid(self, form):
    instance = form.save(commit=False)
    instance.allowed_lang = ','.join(form.cleaned_data['allowed_lang'])
    instance.save()
    if instance.contest_type == 0:
      with transaction.atomic():
        participants = {p.user_id: p for p in instance.contestparticipant_set.all()}
        for sub in instance.submission_set.all():
          start = participants[sub.author_id].start_time(instance)
          end = start + instance.length
          if start <= sub.create_time <= end:
            sub.contest_time = sub.create_time - start
          else:
            sub.contest_time = None
          sub.save(update_fields=["contest_time"])
    return redirect(self.request.path)


class ContestDropStatement(PolygonContestMixin, View):
  def post(self, request, *args, **kwargs):
    self.contest.pdf_statement = None
    self.contest.save(update_fields=['pdf_statement'])
    return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(self.contest.id)}))


class ContestCreate(PolygonBaseMixin, View):
  def post(self, request, *args, **kwargs):
    contest = Contest.objects.create(title='Contest')
    contest.title = 'Contest #%d' % contest.id
    contest.save(update_fields=['title'])
    contest.managers.add(request.user)
    return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(contest.id)}))

class HomeworkClone(PolygonBaseMixin, View):
  def post(self, request, *args, **kwargs):
    try:
      n = request.POST['answer']
      contest = Contest.objects.get(pk=n)
      if not is_contest_manager(request.user, contest):
        raise PermissionError
      if contest.contest_type != 1:
        raise PermissionError
      problem_list = contest.contestproblem_set.all()
      new_hw = Contest.objects.create(title='Contest')
      new_hw.title = 'Contest #%d' % contest.id
      new_hw.save(update_fields=['title'])
      new_hw.managers.add(request.user)
      saved_id = new_hw.id
      contest.id = saved_id
      contest.title = contest.title + ' - 复制'
      contest.create_time = datetime.now()
      contest.save()
      for p in problem_list:
        contest.contestproblem_set.create(identifier=p.identifier, problem_id=p.problem_id, weight=p.weight)
    except:
      messages.error(request, "Homework does not exist or not available.")
      return redirect(reverse('polygon:contest_list'))

    return redirect(reverse('polygon:contest_list') + "?exact=%d" % saved_id)


class ContestAccessManage(PolygonContestMixin, View):
  def post(self, request, pk):
    my_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
    self.contest.managers.clear()
    for key in my_set:
      self.contest.managers.add(User.objects.get(pk=key))
    if self.request.user.pk not in my_set:
      self.contest.managers.add(self.request.user)
    return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))


class ContestAuthorsManage(PolygonContestMixin, View):
  def post(self, request, pk):
    my_set = set(map(int, filter(lambda x: x, request.POST['author'].split(','))))
    self.contest.authors.clear()
    for key in my_set:
      self.contest.authors.add(User.objects.get(pk=key))
    return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))


class ContestVolunteersManage(PolygonContestMixin, View):
  def post(self, request, pk):
    my_set = set(map(int, filter(lambda x: x, request.POST['volunteer'].split(','))))
    self.contest.volunteers.clear()
    for key in my_set:
      self.contest.volunteers.add(User.objects.get(pk=key))
    return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))


class ContestProblemManage(PolygonContestMixin, TemplateView):
  template_name = 'polygon/contest/problem.jinja2'

  def get(self, request, *args, **kwargs):
    if 'data' in request.GET:
      problems = self.contest.contest_problem_list
      data = []
      SUB_FIELDS = ["title", "id", "alias"]
      for problem in problems:
        d = {k: getattr(problem.problem, k) for k in SUB_FIELDS}
        d.update(pid=problem.id, identifier=problem.identifier, weight=problem.weight)
        d["user_ac"] = problem.ac_user_count
        d["user_tot"] = problem.total_user_count
        d["ac"] = problem.ac_count
        d["tot"] = problem.total_count
        d["user_ratio"] = problem.user_ratio
        d["ratio"] = problem.ratio
        data.append(d)
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
      if not Problem.objects.filter(id=problem, visible=True).exists() and \
          not is_admin_or_root(request.user) and \
          not request.user.managing_problems.filter(id=problem).exists():
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


class ContestProblemChangeIdentifier(PolygonContestMixin, View):
  def post(self, request, pk):
    problem = self.contest.contestproblem_set.get(id=request.POST['pid'])
    problem.identifier = request.POST['identifier'].strip()
    problem.save(update_fields=['identifier'])
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
    return redirect(reverse('polygon:contest_invitation', kwargs={'pk': contest.pk}))


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
    return Contest.objects.get(pk=self.kwargs.get('pk')).contestparticipant_set.select_related('user').all()

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


class ContestParticipantStarListToggle(PolygonContestMixin, View):
  def post(self, request, pk):
    with transaction.atomic():
      lst = list(filter(lambda x: x, map(lambda x: x.strip(), request.POST['list'].split('\n'))))
      for x in lst:
        if not x.isdigit():
          raise PermissionDenied
      Contest.objects.get(pk=pk).contestparticipant_set.filter(user_id__in=lst). \
        select_for_update().update(star=True)
    return HttpResponse()


class ContestParticipantClearIP(PolygonContestMixin, View):
  def post(self, request, pk, participant_pk):
    with transaction.atomic():
      participant = Contest.objects.get(pk=pk).contestparticipant_set.select_for_update().get(pk=participant_pk)
      participant.ip_address = None
      participant.save(update_fields=["ip_address"])
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
      while True:
        try:
          username = self._get_username(pk, user_id)
          email = '%s@fake.ecnu.edu.cn' % username
          user = User.objects.create(username=username, email=email)
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


class ContestSystemTestView(PolygonContestMixin, View):
  def post(self, request, pk):
    # almost same as rejudge
    if self.contest.scoring_method in ["subtask", "oi"]:
      submission_set = self.contest.submission_set.all().order_by("create_time")
    else:
      # status private?
      submission_set = self.contest.submission_set.filter(status__in=[SubmissionStatus.ACCEPTED,
                                                                      SubmissionStatus.JUDGING,
                                                                      SubmissionStatus.WAITING,
                                                                      SubmissionStatus.SUBMITTED,
                                                                      SubmissionStatus.PRETEST_PASSED]) \
        .order_by("create_time")

    if len(submission_set) > 0:
      Thread(target=rejudge_submission_set, args=(submission_set,)).start()
    return redirect(reverse('polygon:contest_status', kwargs={'pk': self.contest.id}))


class ContestStatusBackend(PolygonContestMixin, StatusList):
  template_name = 'polygon/contest/status.jinja2'
  contest_submission_visible = True
  privileged = True

  def get_selected_from(self):
    return self.contest.submission_set.all()

  def reinterpret_problem_identifier(self, value):
    return self.contest.contestproblem_set.get(identifier=value).problem_id

  def get_context_data(self, **kwargs):
    data = super(ContestStatusBackend, self).get_context_data(**kwargs)
    data['show_percent'] = self.contest.scoring_method in ('oi',)
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
    return respond_generate_file(request, filename,
                                 file_name_serve_as="ContestParticipant - %s.csv" % self.contest.title)


class ContestAccountDisable(PolygonContestMixin, View):
  def post(self, request, pk, participant_pk):
    contest_participant = get_object_or_404(ContestParticipant, pk=participant_pk)
    contest_participant.is_disabled = not contest_participant.is_disabled
    contest_participant.save(update_fields=['is_disabled'])
    return JsonResponse({})


class ContestParticipantAutoStarView(PolygonContestMixin, View):

  def post(self, request, pk):
    t = request.GET.get('type')
    for participant in self.contest.contestparticipant_set.all():
      starred = False
      if t == "nosub":
        starred = not self.contest.submission_set.filter(author_id=participant.user_id).exists()
      elif t == "nologin":
        starred = participant.user.last_login is None
      if starred:
        participant.star = True
        participant.save(update_fields=['star'])
    return redirect(reverse('polygon:contest_participant', kwargs={"pk": self.contest.id}))


class ContestParticipantFromActivity(PolygonContestMixin, View):

  def post(self, request, pk):
    if request.POST.get("answer") and is_admin_or_root(self.request.user):
      activity = get_object_or_404(Activity, pk=request.POST["answer"])
      with transaction.atomic():
        for participant in activity.activityparticipant_set.filter(is_deleted=False):
          p, _ = self.contest.contestparticipant_set.get_or_create(user=participant.user)
          if not p.comment:
            p.comment = participant.real_name
            p.save(update_fields=['comment'])
    return redirect(reverse('polygon:contest_participant', kwargs={"pk": self.contest.id}))


class ContestGhostRecordImport(PolygonContestMixin, FormView):
  form_class = TestSysUploadForm
  template_name = 'polygon/contest/ghost_import.jinja2'

  def parse_line(self, line):
    if line.startswith("@"):
      try:
        directive, content = re.split(r'\s+', line[1:], 1)
        ret, cur = [], ''
        quote_count = False
        for i in range(len(content)):
          if content[i] == ',' and not quote_count:
            ret.append(cur.strip())
            cur = ''
          elif content[i] == '"':
            quote_count = not quote_count
          else:
            cur += content[i]
        assert not quote_count
        ret.append(cur.strip())
        return (directive.lower(), ret)
      except:
        return None
    return None

  def form_valid(self, form):
    line_counter = 0
    verdict_map = {
      "OK": SubmissionStatus.ACCEPTED,
      "WA": SubmissionStatus.WRONG_ANSWER,
      "RT": SubmissionStatus.RUNTIME_ERROR,
      "TL": SubmissionStatus.TIME_LIMIT_EXCEEDED,
      "ML": SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
      "CE": SubmissionStatus.COMPILE_ERROR,
      "RJ": SubmissionStatus.REJECTED,
    }
    try:
      participant_count = 0
      team_name_map = dict()
      team_id_map = dict()
      submissions = []
      for line in form.cleaned_data["testsys_log"].split("\n"):
        line_counter += 1
        parse_result = self.parse_line(line)
        if parse_result is None:
          continue
        directive, args = parse_result
        print(directive, args)
        if directive == "teams":
          participant_count = int(args[0])
          if participant_count >= 10000:
            raise Exception("队伍数量过多。")
        elif directive == "t":
          team_number = args[0]
          if len(team_name_map) >= participant_count:
            raise Exception("队伍 %s 已经超出了场地容量 %d。" % (team_number, participant_count))
          if team_number in team_name_map:
            raise Exception("队伍 %s 重复注册了。")
          l = len(team_name_map) + 1
          team_name_map[team_number] = (args[3], l)
        elif directive == "s":
          team_number = args[0]
          time_seconds = int(args[3])
          verdict = verdict_map[args[4]]
          if team_number not in team_name_map:
            raise Exception("队伍 %s 没有注册过。" % team_number)
          if not (0 <= time_seconds <= int(round(self.contest.length.total_seconds()))):
            raise Exception("提交时间 %d 不在范围内。" % time_seconds)
          candidate_problem_list = list(filter(lambda x: x.identifier == args[1], self.contest.contest_problem_list))
          if len(candidate_problem_list) != 1:
            raise Exception("'%s' 没找到或者找到了多个相应的题目。" % args[1])
          problem_id = candidate_problem_list[0].problem_id
          submit_time = self.contest.start_time + timedelta(seconds=time_seconds)
          submissions.append((team_number, problem_id, submit_time, verdict))

      if len(team_name_map) != participant_count:
        raise Exception("队伍信息与队伍数量不一致。")

      if participant_count == 0 or len(submissions) == 0:
        raise Exception("没有参赛者或没有提交。")

      with transaction.atomic():
        user_ids = list(User.objects.filter(username__icontains='ghost#').values_list("id", flat=True))
        self.contest.contestparticipant_set.filter(user_id__in=user_ids).delete()
        self.contest.submission_set.filter(author_id__in=user_ids).delete()
        for team_name, team_id in team_name_map.values():
          user, _ = User.objects.get_or_create(username=self.get_ghost_username(team_id),
                                               email=self.get_ghost_username(team_id) + "@ghost.ecnu.edu.cn")
          user.set_unusable_password()
          user.save()
          team_id_map[team_id] = user.id
          self.contest.contestparticipant_set.create(user=user, comment=team_name)
        for team_number, problem_id, submit_time, verdict in submissions:
          _, team_id = team_name_map[team_number]
          s = self.contest.submission_set.create(author_id=team_id_map[team_id],
                                                 status=verdict, problem_id=problem_id,
                                                 contest_time=submit_time - self.contest.start_time,
                                                 lang=None, status_time=None,
                                                 status_percent=100 if verdict == SubmissionStatus.ACCEPTED else 0)
          s.create_time = submit_time
          s.save(update_fields=["create_time"])

      return redirect(reverse('polygon:contest_status', kwargs={'pk': self.contest.pk}))
    except Exception as e:
      messages.error(self.request, "在第 %d 行有错误：" % line_counter + str(e))
      return redirect(self.request.path)

  def get_ghost_username(self, num):
    return "ghost#%04d" % num
