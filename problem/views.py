import json
from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.conf import settings
from django.db.models.functions import TruncDate
from django.db.models.functions import TruncMonth
from django.db.models.functions import TruncYear
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404, reverse, render, Http404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, View, FormView
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from os import path

from django_comments_xtd.models import XtdComment
from django_q.tasks import async
from tagging.models import Tag, TaggedItem, ContentType
from ipware.ip import get_ip

from account.models import User, Payment
from account.payment import download_case, view_report
from account.permissions import is_admin_or_root
from submission.models import Submission, SubmissionStatus, STATUS_CHOICE
from submission.views import render_submission, render_submission_report
from problem.statistics import get_accept_problem_list, get_attempted_problem_list, is_problem_accepted
from utils.comment import CommentForm
from utils.download import respond_as_attachment
from utils.language import LANG_CHOICE
from utils.pagination import EndlessListView
from utils.tagging import edit_string_for_tags
from .models import Problem, Skill, get_input_path, get_output_path
from utils.permission import is_problem_manager, get_permission_for_submission, is_case_download_available
from .statistics import (
    get_many_problem_accept_count, get_problem_accept_count, get_problem_accept_ratio, get_problem_accept_user_count,
    get_problem_accept_user_ratio, get_problem_all_count, get_problem_all_user_count, get_many_problem_difficulty,
    get_problem_difficulty, get_problem_stats,
    get_all_problem_difficulty, get_all_accept_count, get_all_tried_user_count)
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
        else: self.comparing = False
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
            if order_a == 'ascending': ret = ret.order_by('id')
            else: ret = ret.order_by('-id')
        elif order_c == 'name':
            if order_a == 'ascending': ret = ret.order_by('title')
            else: ret = ret.order_by('-title')
        elif order_c == 'upd':
            if order_a == 'ascending': ret = ret.order_by('update_time')
            else: ret = ret.order_by('-update_time')
        elif order_c == 'rw':
            if order_a == 'descending': reverse = True
            else: reverse = False
            all_reward = get_all_problem_difficulty()
            ret = sorted(ret, key=lambda x: all_reward.get(x.id, 0.0), reverse=reverse)
        elif order_c == 'sol':
            if order_a == 'descending': reverse = True
            else: reverse = False
            all_solved, all_tried = get_all_accept_count(), get_all_tried_user_count()
            ret = sorted(ret, key=lambda x: (all_solved.get(x.id, 0), -all_tried.get(x.id, 0)), reverse=reverse)
        elif order_c == 'she' and self.comparing:
            if order_a == 'ascending': reverse = False
            else: reverse = True
            ref = {problem_id: 1 for problem_id in self.her_attempt}
            ref.update({problem_id: -1 for problem_id in self.her_solved})
            ref2 = {problem_id: -1 for problem_id in self.my_attempt}
            ref2.update({problem_id: 1 for problem_id in self.my_solved})
            ret = sorted(ret, key=lambda x: (ref2.get(x.id, 0), ref.get(x.id, 0)), reverse=reverse)
        return ret

    def get_context_data(self, **kwargs):
        data = super(ProblemList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        current_problem_set = [problem.pk for problem in data['problem_list']]
        for problem in data['problem_list']:
            problem.personal_label = 0
        data['show_tags'] = True
        if self.request.user.is_authenticated:
            # Get AC / Wrong
            if self.comparing:
                attempt_list = self.my_attempt
                accept_list = self.my_solved
                for problem in data['problem_list']:
                    if problem.id in self.her_solved:
                        problem.her_label = 1
                    elif problem.id in self.her_attempt:
                        problem.her_label = -1
                    else: problem.her_label = 0
                data['comparing'] = True
                data['compare_user'] = self.compare_user
            else:
                attempt_list = set(get_attempted_problem_list(self.request.user.id))
                accept_list = set(get_accept_problem_list(self.request.user.id))
            for problem in data['problem_list']:
                if problem.id in accept_list:
                    problem.personal_label = 1
                elif problem.id in attempt_list:
                    problem.personal_label = -1

            # get recent unsolved problems
            unsolved_problem_set = set(get_attempted_problem_list(self.request.user.id)) - set(
                get_accept_problem_list(self.request.user.id))
            data['unsolved_submissions'] = unsolved_submissions = []
            for s in self.request.user.submission_set.select_related("problem"). \
                    exclude(status=SubmissionStatus.ACCEPTED).filter(
                problem_id__in=unsolved_problem_set, problem__visible=True). \
                    defer("code", "status_message", "status_detail"):
                if s.problem_id not in unsolved_problem_set:
                    continue
                if s.contest_id:
                    s.contest.add_contest_problem_to_submissions([s])
                unsolved_submissions.append(s)
                unsolved_problem_set.remove(s.problem_id)
                if len(unsolved_submissions) >= 5:
                    break

            if not self.request.user.show_tags:
                data['show_tags'] = False

        # Get Accepted of all users
        problem_ids = list(map(lambda x: x.id, data['problem_list']))
        accept_count = get_many_problem_accept_count(problem_ids)
        difficulties = get_many_problem_difficulty(problem_ids)
        for problem in data['problem_list']:
            problem.accept_count = accept_count[problem.id]
            problem.difficulty = difficulties[problem.id]

        # Get tags
        tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                            .filter(object_id__in=current_problem_set).select_related("tag"))
        for problem in data['problem_list']:
            items = list(filter(lambda x: x.object_id == problem.pk, tagged_items))
            if items:
                problem.my_tags = map(lambda x: x.tag.name, items)
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
            'user_ac_count': get_problem_accept_user_count(self.problem.id),
            'user_all_count': get_problem_all_user_count(self.problem.id),
            'ac_count': get_problem_accept_count(self.problem.id),
            'all_count': get_problem_all_count(self.problem.id),
            'difficulty': get_problem_difficulty(self.problem.id),
            'stats': get_problem_stats(self.problem.id),
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
                raise ValueError("Invalid language.")
            submission = create_submission(self.problem, self.user, request.POST.get('code', ''), lang, ip=get_ip(request))
            running_complete = bool(is_problem_manager(self.user, self.problem) and request.POST.get('complete'))
            async(judge_submission_on_problem, submission, run_until_complete=running_complete)
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

    def get_queryset(self):
        try:
            queryset = self.get_selected_from().select_related('problem', 'author'). \
                only('pk', 'contest_id', 'create_time', 'author_id', 'author__username',
                     'author__magic', 'problem_id', 'problem__title', 'lang', 'status', 'status_time', 'status_percent',
                     'code_length', 'ip', 'cheat_tag', 'status_private', 'status_test')
            if not self.privileged and not self.contest_submission_visible and not is_admin_or_root(self.request.user):
                queryset = queryset.filter(contest__isnull=True, problem__visible=True)

            if 'user' in self.request.GET:
                queryset = queryset.filter(author_id=self.request.GET['user'])
            if self.allow_problem_query and 'problem' in self.request.GET:
                queryset = queryset.filter(problem_id=self.reinterpret_problem_identifier(self.request.GET['problem']))
            if 'lang' in self.request.GET:
                queryset = queryset.filter(lang=self.request.GET['lang'])
            if self.allow_verdict_query and 'verdict' in self.request.GET:
                queryset = queryset.filter(status=int(self.request.GET['verdict'][1:]))

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
            self.request.GET.get('verdict', ''), self.request.GET.get('lang', ''),\
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
        self.ctx["runtime_dist"] = list(map(
            lambda x: {"runtime": x.status_time, "lang": x.get_lang_display()},
            self.problem.submission_set.filter(status=SubmissionStatus.ACCEPTED).defer(
                "code", "status_message", "status_detail")
        ))
        self.ctx["runtime_band_width"] = self.problem.time_limit / 1000 / 25
        try:
            self.ctx["runtime_band_maximum"] = max(self.problem.time_limit / 1000, max(map(lambda x: x["runtime"],
                                                                                           self.ctx["runtime_dist"])))
        except ValueError:
            self.ctx["runtime_band_maximum"] = self.problem.time_limit / 1000

    def get_context_data(self, **kwargs):
        self.ctx = data = super(ProblemStatisticsView, self).get_context_data(**kwargs)
        data['user_ac_count'] = get_problem_accept_user_count(self.problem.id)
        data['user_all_count'] = get_problem_all_user_count(self.problem.id)
        data['user_ratio'] = get_problem_accept_user_ratio(self.problem.id) * 100
        data['ac_count'] = get_problem_accept_count(self.problem.id)
        data['all_count'] = get_problem_all_count(self.problem.id)
        data['ratio'] = get_problem_accept_ratio(self.problem.id) * 100
        data['difficulty'] = get_problem_difficulty(self.problem.id)
        data['stats'] = get_problem_stats(self.problem.id)
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
        if submission.is_judged and is_case_download_available(self.request.user, pk):
            submission.allow_case_download = True
        return HttpResponse(render_submission(submission,
                                              permission=get_permission_for_submission(request.user, submission),
                                              hide_problem=True))


class ProblemSubmissionView(LoginRequiredMixin, TemplateView):

    template_name = 'submission.jinja2'

    def get_context_data(self, **kwargs):
        data = super(ProblemSubmissionView, self).get_context_data(**kwargs)
        data['submission'] = submission = get_object_or_404(Submission, pk=self.kwargs.get('sid'),
                                                                        problem_id=self.kwargs.get('pk'),
                                                                        contest__isnull=True)
        if submission.author == self.request.user and \
                submission.is_judged and is_case_download_available(self.request.user, self.kwargs.get('pk')):
            submission.allow_case_download = True
        if self.request.user.is_authenticated and (
                    submission.author == self.request.user or
                    is_problem_manager(self.request.user,
                                       submission.problem) or
                    self.request.user.submission_set.filter(
                        problem_id=self.kwargs.get('pk'),
                        status=SubmissionStatus.ACCEPTED).exists() or
                    self.request.user.polygon_enabled):
            permission = get_permission_for_submission(self.request.user, submission, special_permission=True)
            data['submission_block'] = render_submission(submission, permission=permission)
            if permission == 2 or (self.request.user == submission.author and submission.report_paid) or \
                    (self.request.user.is_authenticated and self.request.user.polygon_enabled):
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
        return User.objects.only("username", "magic", "score").filter(score__gt=0)

    def get_context_data(self, **kwargs):
        data = super(Millionaires, self).get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            data['my_rank'] = 'N/A'
        else:
            data['my_rank'] = User.objects.filter(score__gte=self.request.user.score).count()
        return data


class SourceList(ListView):
    template_name = 'problem/source.jinja2'
    context_object_name = 'source_list'

    def get_queryset(self):
        queryset = Problem.objects.all()
        if not is_admin_or_root(self.request.user):
            queryset = queryset.filter(visible=True)
        return queryset.only('source').exclude(source='').\
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
def make_payment_for_full_report(request):
    try:
        submission = get_object_or_404(Submission, author_id=request.user.pk, pk=request.POST.get('sub', request.GET['sub']))
        if not is_admin_or_root(request.user):
            if submission.author_id != request.user.pk:
                raise PermissionDenied("This submission does not belong to you.")
            if submission.contest_id and not submission.contest.case_public:
                raise PermissionDenied("Case is not public in this contest.")
        price = 9.9 if submission.contest_id else get_problem_difficulty(submission.problem_id)
        if not path.exists(path.join(settings.GENERATE_DIR, 'submission-%d' % submission.pk)):
            raise PermissionDenied("Case report is not available. Resubmit if necessary.")
        if request.method == 'POST':
            view_report(request.user, price, submission.pk, submission.problem_id, submission.contest_id)
            submission.report_paid = 1
            submission.save(update_fields=['report_paid'])
            return redirect('account:payment')
        else:
            return render(request, 'report_download.jinja2', context={
                'submission': submission.pk,
                'price': price,
            })
    except (ValueError, KeyError):
        raise Http404


@login_required
def case_download_link(request):
    pk = request.GET.get('p')
    fingerprint = get_object_or_404(Payment, pk=pk, user=request.user).detail['fingerprint']
    if request.GET.get('t') == 'in':
        return respond_as_attachment(request, get_input_path(fingerprint), "case.%s.in" % fingerprint[:8])
    elif request.GET.get('t') == 'out':
        return respond_as_attachment(request, get_output_path(fingerprint), "case.%s.out" % fingerprint[:8])
    else:
        raise Http404


@login_required
@require_http_methods(['POST'])
def compare_with(request):
    return redirect(reverse('problem:list') + '?compare=%d&c=she&a=ascending' % get_object_or_404(User, username=request.POST.get('username', '')).pk)
