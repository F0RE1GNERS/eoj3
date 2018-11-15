from datetime import timedelta, datetime

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic.base import ContextMixin
from ipware.ip import get_ip

from blog.models import Blog
from contest.models import Contest, ContestParticipant
from utils.middleware.close_site_middleware import CloseSiteException
from utils.permission import is_contest_manager, is_contest_volunteer
from utils.site_settings import is_site_closed


CONTEST_USER_NOTIFICATION = "NOTIFICATION_%d_%d"


def set_contest_notification(contest_pk, user_pk, optional=2):
    cache.set(CONTEST_USER_NOTIFICATION % (contest_pk, user_pk), optional, None)


def set_many_contest_notification(contest_user_pk_tuples):
    keys = [CONTEST_USER_NOTIFICATION % (cpk, upk) for cpk, upk in contest_user_pk_tuples]
    cache.set_many({key: 2 for key in keys}, None)


def get_contest_notification(contest_pk, user_pk):
    t = cache.get(CONTEST_USER_NOTIFICATION % (contest_pk, user_pk))
    if isinstance(t, int):
        if t >= 2:
            set_contest_notification(contest_pk, user_pk, 1)
        return t
    return 0


def invalidate_contest_notification(contest_pk, user_pk):
    cache.delete(CONTEST_USER_NOTIFICATION % (contest_pk, user_pk))


class BaseContestMixin(ContextMixin, UserPassesTestMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('cid'))
        self.site_closed = is_site_closed(request)
        if self.site_closed:
            if self.contest.contest_type == 1:
                raise CloseSiteException
            if not self.contest.start_time - timedelta(minutes=30) <= timezone.now() \
                    <= self.contest.end_time + timedelta(minutes=10):
                raise CloseSiteException
            if self.contest.access_level >= 30:
                raise CloseSiteException
        self.user = request.user
        self.privileged = is_contest_manager(self.user, self.contest)
        self.volunteer = is_contest_volunteer(self.user, self.contest)
        self.registered, self.vp_available = False, False
        self.virtual_progress, self.participant = None, None        # virtual participation undergoing
        self.participate_start_time = self.contest.start_time       # the start time for the participant
        self.participate_end_time = self.contest.end_time           # the end time for the participant
        self.participate_contest_status = self.contest.status       # the contest status for the participant
        if self.user.is_authenticated:
            try:
                self.participant = self.contest.contestparticipant_set.get(user=self.user)
                self.participate_start_time = self.participant.start_time(self.contest)
                self.participate_end_time = self.participant.end_time(self.contest)
                self.participate_contest_status = self.participant.status(self.contest)
                if self.participant.join_time is not None and self.participate_contest_status == 0:
                    self.virtual_progress = datetime.now() - self.participate_start_time
                if self.contest.ip_sensitive:
                    current_ip = get_ip(request)
                    if self.participant.ip_address is None:
                        self.participant.ip_address = current_ip
                        self.participant.save(update_fields=['ip_address'])
                    self.registered = current_ip == self.participant.ip_address
                else: self.registered = True
            except ContestParticipant.DoesNotExist:
                pass
        if not self.registered and (self.contest.access_level >= 30
                                    or (self.contest.access_level >= 20 and self.contest.status > 0)):
            self.registered = True
        if self.participant is None and self.user.is_authenticated and self.contest.access_level >= 15 and \
                        self.contest.contest_type == 0 and self.contest.status > 0:
            self.vp_available = True
        return super(BaseContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.privileged:
            return True
        if self.contest.access_level == 0:
            self.permission_denied_message = "比赛只对管理员可见。"
            return False
        if self.participate_contest_status < 0:
            self.permission_denied_message = "尚未开始。"
            return False
        if self.registered or self.volunteer:
            return True
        else:
            self.permission_denied_message = "你是不是忘了注册？"
            return False

    def get_context_data(self, **kwargs):
        data = super(BaseContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        if self.user.is_authenticated:
            data['check_new'] = get_contest_notification(self.contest.pk, self.user.pk)
        data['participate_contest_status'] = self.participate_contest_status
        data['current_time'] = datetime.now()
        if self.contest.length is not None:
            data['time_remaining'] = 0
            if self.participate_contest_status < 0:
                data['time_remaining'] = (self.participate_start_time - data['current_time']).total_seconds()
            elif self.participate_contest_status == 0:
                data['time_remaining'] = (self.participate_end_time - data['current_time']).total_seconds()
            data['time_all'], data['remaining_percent'] = 0, 0
            if self.participate_contest_status == 0:
                data['time_all'] = self.contest.length.total_seconds()
                if data['time_all'] > 0:
                    data['remaining_percent'] = data['time_remaining'] / data['time_all']
        data['contest_problem_list'] = self.contest.contest_problem_list
        data['has_permission'] = self.test_func()
        data['is_privileged'] = self.privileged
        data['is_volunteer'] = self.volunteer
        data['show_percent'] = self.contest.scoring_method == 'oi'
        data['site_closed'] = self.site_closed
        data['vp_available'] = self.vp_available
        if self.vp_available:
            ref_time = datetime.now() + timedelta(minutes=6)
            data['vp_start_time'] = datetime(ref_time.year, ref_time.month, ref_time.day, ref_time.hour,
                                             ref_time.minute - ref_time.minute % 5).strftime('%Y-%m-%d %H:%M')
        if self.contest.analysis_blog_id and \
            Blog.objects.filter(pk=self.contest.analysis_blog_id, visible=True).exists():
            data['analysis_available'] = True

        return data
