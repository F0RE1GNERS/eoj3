from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse
from django.utils import timezone
from django.views.generic import TemplateView, View, FormView
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.list import ListView
from django.utils.translation import ugettext_lazy as _

from account.models import User
from account.permissions import is_admin_or_root, is_volunteer
from contest.statistics import recalculate_for_participants, get_participant_rank
from problem.statistics import get_many_problem_accept_count
from submission.statistics import get_accept_problem_list, get_attempted_problem_list
from utils.language import LANG_CHOICE
from utils.middleware.close_site_middleware import CloseSiteException
from utils.permission import is_contest_manager
from utils.site_settings import is_site_closed
from .models import Contest, ContestProblem, ContestInvitation, ContestParticipant, ContestUserRating
from .tasks import add_participant_with_invitation


def time_formatter(seconds):
    return "%d:%.2d:%.2d" % (seconds // 3600,
                             seconds % 3600 // 60,
                             seconds % 60)


class BaseContestMixin(ContextMixin, UserPassesTestMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('cid'))
        if self.contest.always_running and is_site_closed() and not is_admin_or_root(request.user):
            raise CloseSiteException
        self.user = request.user
        self.privileged = is_contest_manager(self.user, self.contest)
        self.volunteer = is_volunteer(self.user)
        if self.user.is_authenticated and self.contest.contestparticipant_set.filter(user=self.user).exists():
            self.registered = True
        elif self.contest.public:
            self.registered = True
        else:
            self.registered = False
        return super(BaseContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.privileged:
            return True
        if not self.contest.visible:
            self.permission_denied_message = _('Contest is not visible.')
            return False
        if self.contest.status < 0:
            self.permission_denied_message = _("Contest hasn't started.")
            return False
        if self.registered:
            return True
        else:
            self.permission_denied_message = _("Did you forget to register for the contest?")
            return False

    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        data['contest_status'] = self.contest.status
        data['current_time'] = timezone.now()
        if not self.contest.always_running:
            data['time_remaining'] = 0
            if data['contest_status'] < 0:
                data['time_remaining'] = (self.contest.start_time - data['current_time']).total_seconds()
            elif data['contest_status'] == 0:
                data['time_remaining'] = (self.contest.end_time - data['current_time']).total_seconds()
            data['time_all'] = 0
            if data['contest_status'] == 0:
                data['time_all'] = (self.contest.end_time - self.contest.start_time).total_seconds()
        data['contest_problem_list'] = self.contest.contest_problem_list
        data['has_permission'] = self.test_func()
        data['is_privileged'] = self.privileged
        data['is_volunteer'] = self.volunteer
        data['show_percent'] = self.contest.scoring_method == 'oi'
        data['site_closed'] = is_site_closed() and not self.privileged

        return data


class DashboardView(BaseContestMixin, TemplateView):
    template_name = 'contest/index.jinja2'

    def test_func(self):
        if self.privileged:
            return True
        return self.contest.visible

    def get_context_data(self, **kwargs):
        data = super(DashboardView, self).get_context_data(**kwargs)

        if self.registered:
            data['registered'] = True
        if self.user.is_authenticated and self.contest.public and self.contest.rated and self.contest.status == -1:
            if self.contest.contestparticipant_set.filter(user=self.user).exists():
                data['public_register'] = 1
            else:
                data['public_register'] = -1

        data['has_permission'] = super(DashboardView, self).test_func()
        for problem in data['contest_problem_list']:
            problem.personal_label = 0
        if data['has_permission'] and self.user.is_authenticated:
            attempt_list = set(get_attempted_problem_list(self.request.user.id, self.contest.id))
            accept_list = set(get_accept_problem_list(self.request.user.id, self.contest.id))
            for problem in data['contest_problem_list']:
                if problem.problem_id in accept_list:
                    problem.personal_label = 1
                elif problem.problem_id in attempt_list:
                    problem.personal_label = -1
                else:
                    problem.personal_label = 0
            if self.contest.always_running:
                all_accept_list = set(get_accept_problem_list(self.request.user.id))
                for problem in data['contest_problem_list']:
                    if problem.problem_id in all_accept_list and problem.personal_label <= 0:
                        problem.personal_label = 2
            if self.privileged:
                clarifications = self.contest.contestclarification_set.all()
            else:
                q = Q(important=True)
                if self.user.is_authenticated:
                    q |= Q(author=self.user)
                clarifications = self.contest.contestclarification_set.filter(q).select_related("author").distinct()
            data["clarifications"] = clarifications
            if not self.contest.always_running:
                try:
                    user_as_participant = self.contest.contestparticipant_set.select_related('user').get(user_id=self.user.pk)
                    self_displayed_rank_template = 'display_rank_cp_%d' % user_as_participant.pk
                    data["rank"] = cache.get(self_displayed_rank_template)
                    if data["rank"] is None:
                        data["rank"] = recalculate_for_participants(self.contest, [self.user.pk], privilege=True).get(self.user.pk)
                        if not self.contest.standings_disabled:
                            data["rank"].update(actual_rank=get_participant_rank(self.contest, self.user.pk))
                        cache.set(self_displayed_rank_template, data["rank"], 15)
                    if data["rank"] is not None:
                        data["rank"].update(user=user_as_participant)
                except ContestParticipant.DoesNotExist:
                    pass

        accept_count = get_many_problem_accept_count(list(map(lambda x: x.problem_id, data['contest_problem_list'])),
                                                     self.contest.id)
        for problem in data['contest_problem_list']:
            problem.accept_count = accept_count[problem.problem_id]

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
        return data


class ContestBoundUser(View):
    def post(self, request, cid):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
        else:
            invitation_code = request.POST.get('code', '')
            try:
                invitation = ContestInvitation.objects.get(code=invitation_code)
                add_participant_with_invitation(cid, invitation.pk, request.user)
                messages.success(request, _('You have successfully joined this contest.'))
            except ContestInvitation.DoesNotExist:
                messages.error(request, _('There seems to be something wrong with your invitation code.'))
        return HttpResponseRedirect(reverse('contest:dashboard', kwargs={'cid': cid}))


class ContestPublicToggleRegister(View):
    def post(self, request, cid):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
        else:
            contest = get_object_or_404(Contest, pk=cid)
            if contest.public and contest.rated and contest.status == -1:
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
        return Contest.objects.get_status_list(show_all=is_admin_or_root(self.request.user), always_running=False)


class ContestAlwaysRunningList(ListView):
    template_name = 'contest/contest_always_running.jinja2'
    paginate_by = 30
    context_object_name = 'contest_list'

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        return Contest.objects.get_status_list(show_all=is_admin_or_root(self.request.user), filter_user=user,
                                               sorting_by_id=True, always_running=True)


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
        else: return User.objects.filter(rating__gt=0).order_by("-rating")[:15]

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