from datetime import timedelta, datetime

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse, redirect
from django.utils.dateparse import parse_datetime
from django.views.generic import TemplateView, View
from django.views.generic.list import ListView
from tagging.models import TaggedItem

from account.models import User
from account.permissions import is_admin_or_root
from contest.base import BaseContestMixin
from contest.statistics import get_participant_score, calculate_problems
from problem.models import Problem
from problem.statistics import get_accept_problem_list, get_attempted_problem_list
from utils.language import LANG_CHOICE
from .models import Contest, ContestProblem, ContestInvitation, ContestUserRating
from .tasks import add_participant_with_invitation


def time_formatter(seconds):
  return "%d:%.2d:%.2d" % (seconds // 3600,
                           seconds % 3600 // 60,
                           seconds % 60)


class DashboardView(BaseContestMixin, TemplateView):
  template_name = 'contest/index.jinja2'

  def test_func(self):
    if self.privileged:
      return True
    return self.contest.access_level > 0

  def get_context_data(self, **kwargs):
    data = super(DashboardView, self).get_context_data(**kwargs)

    if self.registered:
      data['registered'] = True
    if self.user.is_authenticated and self.contest.access_level == 30 and self.contest.status == -1:
      if self.contest.contestparticipant_set.filter(user=self.user).exists():
        data['public_register'] = 1
      else:
        data['public_register'] = -1

    # tags
    data['tagged_contest_problem_list'] = data['contest_problem_list']
    if self.contest.contest_type == 1:
      tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                          .filter(object_id__in=list(map(lambda x: x.problem_id, data['contest_problem_list'])))
                          .select_related("tag"))
      tag_filter = self.request.GET.get("tag")
      if tag_filter:
        data['tagged_contest_problem_list'] = []
      for contest_problem in data['contest_problem_list']:
        items = list(filter(lambda x: x.object_id == contest_problem.problem_id, tagged_items))
        if items:
          contest_problem.tags = list(map(lambda x: x.tag.name, items))
        if tag_filter and hasattr(contest_problem, "tags") and tag_filter in contest_problem.tags:
          data['tagged_contest_problem_list'].append(contest_problem)

    data['has_permission'] = super(DashboardView, self).test_func()
    for problem in data['contest_problem_list']:
      problem.personal_label = 0
    if data['has_permission'] and self.user.is_authenticated:
      # problem red and green status
      attempt_list = set(get_attempted_problem_list(self.request.user.id, self.contest.id))
      accept_list = set(get_accept_problem_list(self.request.user.id, self.contest.id))
      for problem in data['contest_problem_list']:
        if problem.problem_id in accept_list:
          problem.personal_label = 1
        elif problem.problem_id in attempt_list:
          problem.personal_label = -1
        else:
          problem.personal_label = 0
      if self.contest.contest_type == 1:
        all_accept_list = set(get_accept_problem_list(self.request.user.id))
        for problem in data['contest_problem_list']:
          if problem.problem_id in all_accept_list and problem.personal_label <= 0:
            problem.personal_label = 2

      # show display rank
      if self.contest.contest_type == 0:
        if self.participant is not None:
          self_displayed_rank_template = 'display_rank_cp_%d' % self.participant.pk
          data["rank"] = cache.get(self_displayed_rank_template)
          if data["rank"] is None:
            if self.virtual_progress is not None:
              data["rank"] = get_participant_score(self.contest, self.user.pk, self.virtual_progress)
            else:
              data["rank"] = get_participant_score(self.contest, self.user.pk)
            if self.contest.common_status_access_level < 0:
              data["rank"].pop("actual_rank", None)
            cache.set(self_displayed_rank_template, data["rank"], 15)
          if data["rank"] is not None:
            data["rank"].update(user=self.participant)

    # make sure problem status is correct (for VP purpose)
    if self.virtual_progress is not None:
      calculate_problems(self.contest, self.contest.contest_problem_list, self.virtual_progress)
    # `contest.contest_problem_list` is data["contest_problem_list"]. Same thing.
    if self.contest.scoring_method == "oi":
      data['enable_scoring'] = True
      for problem in data['contest_problem_list']:
        problem.max_score = int(round(problem.max_score / 100 * problem.weight))
        problem.avg_score = round(problem.avg_score / 100 * problem.weight, 1)

    data['authors'] = self.contest.authors.all()

    # color settings
    data['level_colors'] = ["", "green", "teal", "blue", "orange", "red"]

    return data


class ContestProblemDetail(BaseContestMixin, TemplateView):
  template_name = 'contest/problem.jinja2'

  def get_context_data(self, **kwargs):
    data = super(ContestProblemDetail, self).get_context_data(**kwargs)
    data['contest_problem'] = get_object_or_404(ContestProblem,
                                                identifier=self.kwargs.get('pid'),
                                                contest=self.contest)
    data['problem'] = data['contest_problem'].problem

    # submit part
    data['lang_choices'] = list(filter(lambda k: k[0] in self.contest.supported_language_list, LANG_CHOICE))
    # if self.request.user.is_authenticated:
    #     data['attempt_left'] = settings.SUBMISSION_ATTEMPT_LIMIT - self.contest.submission_set.filter(
    #         author=self.request.user,
    #         problem_id=data['contest_problem'].problem_id).count()
    #     if self.contest.status != 0:
    #         data['attempt_left'] = settings.SUBMISSION_ATTEMPT_LIMIT
    return data


class ContestStatements(BaseContestMixin, View):
  def get(self, request, *args, **kwargs):
    if not self.contest.pdf_statement:
      raise Http404
    return HttpResponse(self.contest.pdf_statement.read(), content_type="application/pdf")


class ContestBoundUser(View):
  def post(self, request, cid):
    if not request.user.is_authenticated:
      messages.error(request, "请先登录。")
    else:
      invitation_code = request.POST.get('code', '')
      try:
        invitation = ContestInvitation.objects.get(code=invitation_code)
        add_participant_with_invitation(cid, invitation.pk, request.user)
        messages.success(request, "你已成功加入。")
      except ContestInvitation.DoesNotExist:
        messages.error(request, "邀请码有误。")
    return HttpResponseRedirect(reverse('contest:dashboard', kwargs={'cid': cid}))


class ContestPublicToggleRegister(View):
  def post(self, request, cid):
    if not request.user.is_authenticated:
      messages.error(request, "请先登录。")
    else:
      contest = get_object_or_404(Contest, pk=cid)
      if contest.access_level == 30 and contest.status == -1:
        with transaction.atomic():
          if not contest.contestparticipant_set.filter(user=request.user).exists():
            contest.contestparticipant_set.get_or_create(user=request.user)
          else:
            contest.contestparticipant_set.filter(user=request.user).delete()
    return HttpResponseRedirect(reverse('contest:dashboard', kwargs={'cid': cid}))


class ContestList(ListView):
  template_name = 'contest/contest_list.jinja2'
  paginate_by = 30
  context_object_name = 'contest_list'

  def get_queryset(self):
    return Contest.objects.get_status_list(show_all=is_admin_or_root(self.request.user), contest_type=0)

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data["hide_header"] = True
    return data


class ContestGymList(ListView):
  template_name = 'contest/contest_gym_list.jinja2'
  paginate_by = 30
  context_object_name = 'contest_list'

  def get_queryset(self):
    user = self.request.user if self.request.user.is_authenticated else None
    return Contest.objects.get_status_list(show_all=is_admin_or_root(self.request.user), filter_user=user,
                                           sorting_by_id=True, contest_type=1)

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data["hide_header"] = True
    return data


class ContestRatings(ListView):
  template_name = 'contest/contest_ratings.jinja2'
  context_object_name = 'global_rating'
  paginate_by = 100

  def dispatch(self, request, *args, **kwargs):
    q = request.GET.get('q', '')
    if request.GET.get('full'):
      self.full = True
    elif q.isdigit():
      self.user = get_object_or_404(User, pk=q)
      self.full = False
    elif request.user.is_authenticated:
      self.user = request.user
      self.full = False
    else:
      self.full = True
    return super().dispatch(request, *args, **kwargs)

  def get_queryset(self):
    if self.full:
      return User.objects.filter(rating__gt=0).order_by("-rating")
    else:
      return User.objects.filter(rating__gt=0).order_by("-rating")[:15]

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data['full'] = self.full
    if not self.full:
      data['query_user'] = self.user
      data['max_rating'], data['min_rating'] = 2000, 1000
      data['rating_list'] = ContestUserRating.objects.select_related('contest').filter(user=self.user)
      if data['rating_list']:
        data['max_rating'] = max(data['max_rating'], max(map(lambda x: x.rating, data['rating_list'])))
        data['min_rating'] = min(data['min_rating'], max(map(lambda x: x.rating, data['rating_list'])))
    return data


class ContestVirtualParticipantJoin(BaseContestMixin, View):

  def test_func(self):
    return self.vp_available

  def post(self, request, *args, **kwargs):
    start_time = parse_datetime(request.POST["time"])
    redirect_link = reverse('contest:dashboard', kwargs={'cid': self.contest.pk})
    if start_time <= datetime.now():
      messages.error(request, "输入时间应晚于当前时间。")
      return redirect(redirect_link)
    if start_time - datetime.now() > timedelta(days=1):
      messages.error(request, "不支持预约 24 小时以后的比赛。")
      return redirect(redirect_link)
    self.contest.contestparticipant_set.create(user=self.request.user, join_time=start_time)
    return redirect(redirect_link)
