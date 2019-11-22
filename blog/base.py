from datetime import timedelta

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone


from account.permissions import is_admin_or_root
from blog.models import Blog
from contest.models import ContestParticipant
from utils.middleware.close_site_middleware import CloseSiteException
from utils.permission import is_contest_volunteer, is_contest_manager
from utils.site_settings import is_site_closed


class BlogMixin(UserPassesTestMixin):
  def dispatch(self, request, *args, **kwargs):
    blogs = Blog.objects.with_likes().with_dislikes().with_likes_flag(request.user)
    self.blog = get_object_or_404(blogs, pk=kwargs.get('pk'))
    self.user = request.user
    if self.blog.is_reward and self.blog.contest:
      self.site_closed = is_site_closed(request)
      self.contest = self.blog.contest
      if self.site_closed:
        if self.contest.contest_type == 1:
          raise CloseSiteException
        if not self.contest.start_time - timedelta(minutes=30) <= timezone.now() \
               <= self.contest.end_time + timedelta(minutes=10):
          raise CloseSiteException
        if self.contest.access_level >= 30:
          raise CloseSiteException
      self.privileged = is_contest_manager(self.user, self.contest)
      self.volunteer = is_contest_volunteer(self.user, self.contest)
      self.registered = False
      self.virtual_progress, self.participant = None, None
      self.participate_start_time = self.contest.start_time
      self.participate_end_time = self.contest.end_time
      self.participate_contest_status = self.contest.status
      if self.user.is_authenticated:
        try:
          self.participant = self.contest.contestparticipant_set.get(user=self.user)
          self.participate_start_time = self.participant.start_time(self.contest)
          self.participate_end_time = self.participant.end_time(self.contest)
          self.participate_contest_status = self.participant.status(self.contest)
          if self.participant is not None:
            self.registered = True
        except ContestParticipant.DoesNotExist:
          pass
      if not self.registered and (self.contest.access_level >= 30
                                  or (self.contest.access_level >= 20 and self.contest.status > 0)):
        self.registered = True
    return super(BlogMixin, self).dispatch(request, *args, **kwargs)

  def test_func(self):
    if self.blog.is_reward:
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
    else:
      if is_admin_or_root(self.user):
        return True
      if self.user == self.blog.author or self.blog.visible:
        return True
    return False
