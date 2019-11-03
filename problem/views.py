import random
from collections import defaultdict

import django_comments
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404, reverse, Http404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, View, FormView
from django.views.generic.base import ContextMixin, TemplateResponseMixin, RedirectView
from django.views.generic.list import ListView
from django_comments_xtd.models import XtdComment
from django_q.tasks import async_task
from ipware.ip import get_ip
from tagging.models import Tag, TaggedItem, ContentType
from blog.models import Blog

from account.models import User
from account.permissions import is_admin_or_root
from dispatcher.models import Server
from problem import recommendation
from problem.commons.problem_list_helper import attach_personal_solve_info, attach_tag_info
from problem.models.feedback import FeedbackCompare
from problem.statistics import get_accept_problem_list, get_attempted_problem_list, is_problem_accepted
from submission.models import Submission
from submission.util import SubmissionStatus, STATUS_CHOICE
from submission.views import render_submission, render_submission_report
from utils.comment import CommentForm
from utils.language import LANG_CHOICE
from utils.permission import is_problem_manager, get_permission_for_submission, is_case_download_available
from utils.tagging import edit_string_for_tags
from .models import Problem, Skill, UserStatus
from .tasks import create_submission, judge_submission_on_problem


class ProblemList(ListView):
  template_name = 'problem/index.jinja2'
  paginate_by = 100
  context_object_name = 'problem_list'

  def get_queryset(self):
    source = self.request.GET.get('source')
    kw = self.request.GET.get('keyword')
    tg = self.request.GET.get('tag')
    order_c = self.request.GET.get('c', 'id')
    order_a = self.request.GET.get('a', 'descending')
    compare_with = self.request.GET.get('compare', '')

    if order_c not in ['id', 'name', 'rw', 'sol', 'she'] or order_a not in ['ascending', 'descending']:
      raise PermissionDenied("Invalid order")
    if tg:
      tag = get_object_or_404(Tag, name=tg)
      queryset = TaggedItem.objects.get_by_model(Problem, tag)
      if hasattr(tag, 'taginfo'):
        self.tag_info = {
          "name": tag.name,
          "description": tag.taginfo.description
        }
    else:
      queryset = Problem.objects.all()
    if self.request.user.is_authenticated and compare_with and compare_with.isdigit():
      self.compare_user = get_object_or_404(User, pk=compare_with)
      self.her_attempt = set(get_attempted_problem_list(compare_with))
      self.her_solved = set(get_accept_problem_list(compare_with))
      self.my_attempt = set(get_attempted_problem_list(self.request.user.id))
      self.my_solved = set(get_accept_problem_list(self.request.user.id))
      queryset = queryset.filter(pk__in=self.her_attempt | self.her_solved | self.my_attempt | self.my_solved)
      self.comparing = True
      self.paginate_by = 200
    else:
      self.comparing = False
    if source:
      queryset = queryset.filter(source=source)
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
          queryset |= TaggedItem.objects.get_by_model(Problem, tag.first())

    ret = queryset.defer("description", "input", "output", "hint").distinct()
    if order_c == 'id':
      if order_a == 'ascending':
        ret = ret.order_by('id')
      else:
        ret = ret.order_by('-id')
    elif order_c == 'name':
      if order_a == 'ascending':
        ret = ret.order_by('title')
      else:
        ret = ret.order_by('-title')
    elif order_c == 'upd':
      if order_a == 'ascending':
        ret = ret.order_by('update_time')
      else:
        ret = ret.order_by('-update_time')
    elif order_c == 'rw':
      if order_a == 'descending':
        ret = ret.order_by("-reward")
      else:
        ret = ret.order_by("reward")
    elif order_c == 'sol':
      if order_a == 'descending':
        ret = ret.order_by("-ac_user_count")
      else:
        ret = ret.order_by("ac_user_count")
    elif order_c == 'she' and self.comparing:
      if order_a == 'ascending':
        reverse = False
      else:
        reverse = True
      ref = {problem_id: 1 for problem_id in self.her_attempt}
      ref.update({problem_id: -1 for problem_id in self.her_solved})
      ref2 = {problem_id: -1 for problem_id in self.my_attempt}
      ref2.update({problem_id: 1 for problem_id in self.my_solved})
      ret = sorted(ret, key=lambda x: (ref2.get(x.id, 0), ref.get(x.id, 0)), reverse=reverse)
    return ret

  def get_context_data(self, **kwargs):
    data = super(ProblemList, self).get_context_data(**kwargs)
    data['keyword'] = self.request.GET.get('keyword')
    data['show_tags'] = True
    for problem in data["problem_list"]:
      problem.personal_label = 0
    if self.request.user.is_authenticated:
      # Get AC / Wrong
      if self.comparing:
        for problem in data['problem_list']:
          if problem.id in self.her_solved:
            problem.her_label = 1
          elif problem.id in self.her_attempt:
            problem.her_label = -1
          else:
            problem.her_label = 0
        data['comparing'] = True
        data['compare_user'] = self.compare_user
      attach_personal_solve_info(data["problem_list"], self.request.user.id)

      if not self.request.user.show_tags:
        data['show_tags'] = False

    # Get tags
    attach_tag_info(data["problem_list"])
    if hasattr(self, "tag_info"):
      data["tag_info"] = self.tag_info

    data['tags'] = Tag.objects.usage_for_model(Problem, counts=True)

    return data


class ProblemDetailMixin(TemplateResponseMixin, ContextMixin, UserPassesTestMixin):

  def dispatch(self, request, *args, **kwargs):
    self.problem = get_object_or_404(Problem, pk=kwargs.get('pk'))
    self.user = request.user
    self.privileged = is_problem_manager(self.user, self.problem)
    self.request = request
    return super(ProblemDetailMixin, self).dispatch(request, *args, **kwargs)

  def test_func(self):
    return self.privileged or self.problem.visible

  def get_context_data(self, **kwargs):
    data = super(ProblemDetailMixin, self).get_context_data(**kwargs)
    data['problem'] = self.problem
    data['is_privileged'] = self.privileged
    data['discussion_count'] = XtdComment.objects.filter(content_type=ContentType.objects.get_for_model(Problem),
                                                         object_pk=self.problem.pk,
                                                         site__pk=settings.SITE_ID,
                                                         is_public=True,
                                                         is_removed=False,
                                                         level=0).count()
    return data


class DiscussionView(ProblemDetailMixin, FormView):
  template_name = 'problem/detail/discussion.jinja2'
  form_class = CommentForm

  def get_context_data(self, **kwargs):
    data = super(DiscussionView, self).get_context_data(**kwargs)
    data['action_path'] = reverse('comments-post-comment')
    return data

  def get_form_kwargs(self):
    kw = super(DiscussionView, self).get_form_kwargs()
    kw['target_object'] = self.problem
    return kw


class ProblemView(ProblemDetailMixin, TemplateView):
  def get_template_names(self):
    if self.request.GET.get('onlytag'):
      return ['problem/detail/tag.jinja2']
    else:
      return ['problem/detail/problem.jinja2']

  def get_submit_data(self):
    data = {}
    submission_pk = self.request.GET.get('submission', None)
    if submission_pk:
      submission = Submission.objects.get(pk=submission_pk)
      if get_permission_for_submission(self.request.user, submission):
        data['code'] = submission.code
    data['lang_choices'] = LANG_CHOICE
    data['default_problem'] = self.problem.pk
    return data

  def get_stats(self):
    data = {
      'user_ac_count': self.problem.ac_user_count,
      'user_all_count': self.problem.total_user_count,
      'ac_count': self.problem.ac_count,
      'all_count': self.problem.total_count,
      'difficulty': self.problem.reward,
      'stats': self.problem.stats,
    }
    try:
      last_sub_time = self.problem.submission_set.first().create_time
    except:
      last_sub_time = None
    data.update(last_sub_time=last_sub_time)
    return data

  def get_tag_info(self):
    return {
      'tags': edit_string_for_tags(self.problem.tags),
      'tags_choices': Tag.objects.all().values_list("name", flat=True),
      'public_edit_access': self.privileged or is_problem_accepted(self.request.user, self.problem)
    }

  def get_context_data(self, **kwargs):
    data = super(ProblemView, self).get_context_data()
    data['problem'] = self.problem

    show_tags = True
    if self.request.user.is_authenticated:
      show_tags = self.request.user.show_tags
    if show_tags:
      data['tags_list'] = self.problem.tags
      data['show_tags'] = True
    data.update(self.get_tag_info())

    if 'onlytag' not in self.request.GET:
      data.update(self.get_submit_data())
      data.update(self.get_stats())

    return data


class ProblemSubmitView(ProblemDetailMixin, View):
  def test_func(self):
    return super(ProblemSubmitView, self).test_func() and self.user.is_authenticated

  def post(self, request, pk):
    try:
      lang = request.POST.get('lang', '')
      if lang not in dict(LANG_CHOICE).keys():
        raise ValueError("语言无效。")
      submission = create_submission(self.problem, self.user, request.POST.get('code', ''), lang, ip=get_ip(request))
      running_complete = bool(is_problem_manager(self.user, self.problem) and request.POST.get('complete'))
      async_task(judge_submission_on_problem, submission, run_until_complete=running_complete)
      return JsonResponse({"url": reverse('problem:submission_api',
                                          kwargs={'pk': self.problem.id, 'sid': submission.id})})
    except Exception as e:
      return HttpResponseBadRequest(str(e).encode())


class StatusList(ListView):
  template_name = 'problem/status.jinja2'
  paginate_by = 50
  context_object_name = 'submission_list'
  allow_problem_query = True
  allow_verdict_query = True
  query_number = 5000
  distinct_by_author = False  # query number should not be too large when this is true
  contest_submission_visible = False
  privileged = False

  def get_selected_from(self):
    return Submission.objects.all()

  def reinterpret_problem_identifier(self, value):
    return value

  def get_ordering(self):
    return "-create_time"

  def get_queryset(self):
    try:
      queryset = self.get_selected_from().select_related('problem', 'author'). \
        only('pk', 'contest_id', 'create_time', 'author_id', 'author__username',
             'author__magic', 'problem_id', 'problem__title', 'lang', 'status', 'status_time', 'status_percent',
             'code_length', 'ip', 'status_test', 'status_memory', 'visible', 'judge_server', 'contest_time')

      if 'user' in self.request.GET:
        queryset = queryset.filter(author_id=self.request.GET['user'])
      if self.allow_problem_query and 'problem' in self.request.GET:
        problem_id = self.reinterpret_problem_identifier(self.request.GET['problem'])
        try:
          if is_problem_manager(self.request.user, Problem.objects.get(pk=problem_id)):
            self.privileged = True
          queryset = queryset.filter(problem_id=problem_id)
        except:
          pass
      if 'lang' in self.request.GET:
        queryset = queryset.filter(lang=self.request.GET['lang'])
      if self.allow_verdict_query and 'verdict' in self.request.GET:
        queryset = queryset.filter(status=int(self.request.GET['verdict'][1:]))

      if is_admin_or_root(self.request.user):
        self.privileged = True
      if not self.privileged:
        queryset = queryset.filter(visible=True)
      if not self.privileged and not self.contest_submission_visible:
        queryset = queryset.filter(contest__isnull=True)

      ordering = self.get_ordering()
      if ordering is not None:
        if isinstance(ordering, str):
          ordering = (ordering,)
        queryset = queryset.order_by(*ordering)

      if self.distinct_by_author:
        author_set = set()
        res = []
        for submission in queryset.all():
          if submission.author_id not in author_set:
            author_set.add(submission.author_id)
            res.append(submission)
            if self.query_number and len(res) >= self.query_number:
              break
        return res
      else:
        return queryset.all()[:self.query_number]
    except Exception as e:
      raise Http404(e)

  def get_context_data(self, **kwargs):
    data = super(StatusList, self).get_context_data(**kwargs)
    user = self.request.user
    data['keyword'] = self.request.GET.get('keyword')
    data['param_verdict'], data['param_lang'], data['param_user'], data['param_problem'] = \
      self.request.GET.get('verdict', ''), self.request.GET.get('lang', ''), \
      self.request.GET.get('user', ''), self.request.GET.get('problem', '')
    data['allow_verdict_query'] = self.allow_verdict_query
    data['lang_choices'] = LANG_CHOICE
    data['verdict_choices'] = STATUS_CHOICE

    if user.is_authenticated:
      for submission in data['submission_list']:
        if is_admin_or_root(user) or submission.author == user:
          submission.is_privileged = True
    return data


class ProblemStatisticsView(ProblemDetailMixin, StatusList):
  template_name = 'problem/detail/statistics.jinja2'
  paginate_by = None
  allow_problem_query = False
  allow_verdict_query = False
  query_number = 10
  distinct_by_author = True
  contest_submission_visible = True

  def get_selected_from(self):
    if self.request.GET.get('type') == 'shortest':
      return self.problem.submission_set.filter(status=SubmissionStatus.ACCEPTED).order_by("code_length")
    elif self.request.GET.get('type') == 'fastest':
      return self.problem.submission_set.filter(status=SubmissionStatus.ACCEPTED).order_by("status_time")
    else:
      return self.problem.submission_set.filter(status=SubmissionStatus.ACCEPTED).order_by("-create_time")

  def get_runtime_distribution(self):
    exclude_q = Q(code_length__isnull=True) | Q(status_time__isnull=True)
    self.ctx["runtime_data"] = self.problem.submission_set \
      .only("lang", "code_length", "status_memory", "status_time", "author_id", "contest_id", "problem_id") \
      .filter(status=SubmissionStatus.ACCEPTED, visible=True).exclude(exclude_q)
    if self.request.user.is_authenticated:
      for s in self.ctx["runtime_data"]:
        s.mine = s.author_id == self.request.user.pk
    for s in self.ctx["runtime_data"]:
      if s.contest_id:
        s.link = reverse("contest:submission", kwargs={"cid": s.contest_id, "sid": s.id})
      else:
        s.link = reverse("problem:submission", kwargs={"pk": s.problem_id, "sid": s.id})
      s.mine = s.author_id == self.request.user.pk

  def get_context_data(self, **kwargs):
    self.ctx = data = super(ProblemStatisticsView, self).get_context_data(**kwargs)

    judge_servers = {server.pk: server.name for server in Server.objects.all()}
    for s in data['submission_list']:
      s.judge_server = judge_servers.get(s.judge_server, "N/A")

    data['user_ac_count'] = self.problem.ac_user_count
    data['user_all_count'] = self.problem.total_user_count
    data['user_ratio'] = self.problem.ac_user_ratio * 100
    data['ac_count'] = self.problem.ac_count
    data['all_count'] = self.problem.total_count
    data['ratio'] = self.problem.ac_ratio * 100
    data['difficulty'] = self.problem.reward
    data['stats'] = self.problem.stats
    data['param_type'] = self.request.GET.get('type', 'latest')
    data['tags'] = edit_string_for_tags(self.problem.tags)
    data['tags_choices'] = Tag.objects.all().values_list("name", flat=True)
    data['public_edit_access'] = is_problem_accepted(self.request.user, self.problem)
    data['all_valid'] = True
    self.get_runtime_distribution()

    return data


class ProblemUpdateTags(ProblemDetailMixin, View):
  @staticmethod
  def clear_tags(text):
    return ''.join(list(map(lambda x: x + ',', filter(lambda u: Tag.objects.filter(name=u).exists(),
                                                      map(lambda t: t.strip(), text.split(',')))))[:5])

  def post(self, request, *args, **kwargs):
    if not is_problem_accepted(self.request.user, self.problem):
      raise PermissionDenied
    tags = self.__class__.clear_tags(request.POST['tags'])
    if tags:
      Tag.objects.update_tags(self.problem, tags)
    return redirect(request.POST['next'])


class ProblemPersonalOlderSubmissionsAPI(UserPassesTestMixin, TemplateView):
  template_name = 'components/past_submissions.jinja2'

  def test_func(self):
    return self.request.user.is_authenticated

  def get_context_data(self, **kwargs):
    submission_set = Submission.objects.defer("code", "status_message", "status_detail"). \
      filter(author_id=self.request.user.pk, problem_id=kwargs.get('pk'))
    return {'submission_list': submission_set}


class ProblemSubmissionAPI(LoginRequiredMixin, View):

  def get(self, request, pk, sid):
    submission = get_object_or_404(Submission, problem_id=pk, author=self.request.user, pk=sid)
    if submission.is_judged:
      if is_case_download_available(self.request.user, pk):
        submission.allow_case_download = True
      if SubmissionStatus.is_accepted(submission.status):
        recommended_problems = recommendation.coming_up_magic_problems(submission.author_id)
        if recommended_problems:
          submission.next_problem = recommended_problems[0]
    return HttpResponse(render_submission(submission,
                                          permission=get_permission_for_submission(request.user, submission),
                                          hide_problem=True,
                                          rejudge_available=False,
                                          hide_reward=True))


class ProblemSubmissionView(LoginRequiredMixin, TemplateView):
  template_name = 'submission.jinja2'

  def get_context_data(self, **kwargs):
    data = super(ProblemSubmissionView, self).get_context_data(**kwargs)
    data['submission'] = submission = get_object_or_404(Submission, pk=self.kwargs.get('sid'),
                                                        problem_id=self.kwargs.get('pk'),
                                                        contest__isnull=True)
    if self.request.user.is_authenticated and (
            submission.author == self.request.user or
            is_problem_manager(self.request.user,
                               submission.problem) or
            self.request.user.submission_set.filter(
              problem_id=self.kwargs.get('pk'),
              status=SubmissionStatus.ACCEPTED).exists() or
            self.request.user.has_coach_access()):
      permission = get_permission_for_submission(self.request.user, submission, special_permission=True)
      data['submission_block'] = render_submission(submission, permission=permission)
      if permission == 2 or self.request.user == submission.author:
        data['report_block'] = render_submission_report(submission.pk)
      else:
        data['report_block'] = ''
    else:
      raise PermissionDenied("Code is not public for users who have not got accepted yet.")
    data['problem'] = submission.problem
    return data


class Millionaires(ListView):
  template_name = 'problem/standings.jinja2'
  paginate_by = 100
  context_object_name = 'rank_list'

  def get_queryset(self):
    return User.objects.only("username", "magic", "score").filter(score__gt=0).exclude(username__contains='#')

  def get_context_data(self, **kwargs):
    user_solved = {r.user_id: r.ac_distinct_count for r in UserStatus.objects.filter(contest_id=0)}
    data = super(Millionaires, self).get_context_data(**kwargs)
    if not self.request.user.is_authenticated:
      data['my_rank'] = 'N/A'
    else:
      data['my_rank'] = User.objects.filter(score__gte=self.request.user.score).exclude(username__contains='#').count()
    for user in data['rank_list']:
      user.solved = user_solved.get(user.id, 0)
    return data


class SourceList(ListView):
  template_name = 'problem/source.jinja2'
  context_object_name = 'source_list'

  def get_queryset(self):
    queryset = Problem.objects.all()
    if not is_admin_or_root(self.request.user):
      queryset = queryset.filter(visible=True)
    return queryset.only('source').exclude(source=''). \
      order_by('source').values('source').annotate(count=Count('source'))


class ArchiveList(TemplateView):
  template_name = 'problem/archive.jinja2'

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    skill_list = Skill.objects.order_by("-priority").all()
    children_list = defaultdict(list)
    problem_list = defaultdict(list)
    problem_set = set()
    for skill in skill_list:
      children_list[skill.parent_id].append(skill.pk)
      problem_list[skill.pk] = skill.parsed_problem_list
      problem_set = problem_set.union(skill.parsed_problem_list)
    problem_set = {problem.pk: problem for problem in Problem.objects.only("title").filter(pk__in=problem_set)}
    skill_list = {skill.pk: skill for skill in skill_list}
    attempt_list = set(get_attempted_problem_list(self.request.user.id))
    accept_list = set(get_accept_problem_list(self.request.user.id))
    for problem in problem_set.values():
      if problem.pk in accept_list:
        problem.personal_label = 1
      elif problem.pk in attempt_list:
        problem.personal_label = -1
    data.update(children_list=children_list, problem_list=problem_list, problem_set=problem_set, skill_list=skill_list)
    return data


@login_required
@require_http_methods(['POST'])
def compare_with(request):
  return redirect(reverse('problem:list') + '?compare=%d&c=she&a=ascending' % get_object_or_404(User,
                                                                                                username=request.POST.get(
                                                                                                  'username', '')).pk)


class ProblemRecommendation(LoginRequiredMixin, TemplateView):
  template_name = "problem/recommendation.jinja2"


def get_context_data(self, **kwargs):
  data = super().get_context_data(**kwargs)
  data["recommended_problems"] = recommendation.coming_up_magic_problems(self.request.user.id)
  data["trending_problems"] = recommendation.trending_problems(self.request.user.id)
  data["unsolved_problems"] = recommendation.unsolved_problems(self.request.user.id)
  data["hard_problems"] = recommendation.hard_problems(self.request.user.id)
  data["med_problems"] = recommendation.med_problems(self.request.user.id)
  data["unfamiliar_problems"] = recommendation.unfamiliar_problems(self.request.user.id)
  data["familiar_problems"] = recommendation.familiar_problems(self.request.user.id)
  return data


class RuledRedirectView(RedirectView):
  def get_redirect_url(self, *args, **kwargs):
    if self.request.user.is_authenticated:
      self.pattern_name = "problem:recommendation"
    else:
      self.pattern_name = "problem:list"
    return super().get_redirect_url(*args, **kwargs)


class ProblemFeedbackCompare(LoginRequiredMixin, TemplateView):
  template_name = "problem/feedback/compare.jinja2"

  def post(self, request, *args, **kwargs):
    FeedbackCompare.objects.create(user=self.request.user,
                                   problem_1=int(self.request.POST["problem1"]),
                                   problem_2=int(self.request.POST["problem2"]))
    return redirect(self.request.path)

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    accept_problems = list(Problem.objects.filter(id__in=get_accept_problem_list(self.request.user.pk),
                                                  visible=True).values_list("id", flat=True))
    if len(accept_problems) < 2:
      raise PermissionDenied
    random.shuffle(accept_problems)
    data["problem1"] = Problem.objects.get(id=accept_problems[0])
    data["problem2"] = Problem.objects.get(id=accept_problems[1])
    return data

class ProblemReward(ListView):
  template_name = 'problem/reward.jinja2'
  context_object_name = 'reward_list'

  def get_queryset(self):
    return Blog.objects.filter(is_reward=True, contest=None).with_likes().with_likes_flag(self.request.user)

  def get_context_data(self, **kwargs):
    data = super(ProblemReward, self).get_context_data(**kwargs)
    return data