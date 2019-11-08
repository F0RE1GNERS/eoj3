from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import reverse, redirect, get_object_or_404
from django.views.generic import ListView
from django.views.generic import View

from contest.base import BaseContestMixin, set_contest_notification, set_many_contest_notification, \
  get_contest_notification, invalidate_contest_notification
from utils.permission import is_contest_manager
from .models import ContestClarification

BUILTIN_CHOICES = [
  ('yes', "Yes"),
  ('no', "No"),
  ('read', "Read the problem statement carefully."),
  ('invalid', "I don't understand your question."),
  ('nocomment', "No comment."),
  ('custom', 'Custom')
]


class ContestNotificationCheck(View):
  def get(self, request, cid):
    if not request.user.is_authenticated:
      raise PermissionDenied
    contest_id = int(cid)
    if not 1 <= contest_id <= 2E9:  # not reasonable
      raise PermissionDenied
    t = get_contest_notification(contest_id, request.user.pk)
    return HttpResponse(str(t), content_type='text/plain')


class ContestClarificationList(BaseContestMixin, ListView):
  context_object_name = 'clarifications'
  template_name = 'contest/clarification.jinja2'

  def test_func(self):
    return super().test_func() and self.request.user.is_authenticated

  def get_queryset(self):
    if self.privileged:
      return self.contest.contestclarification_set.all()
    else:
      q = Q(important=True)
      if self.user.is_authenticated:
        q |= Q(author=self.user)
      return self.contest.contestclarification_set.filter(q).select_related("author").distinct()

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    invalidate_contest_notification(self.contest.pk, self.request.user.pk)
    data["check_new"] = 0
    data["BUILTIN_CHOICES"] = BUILTIN_CHOICES
    return data


class ContestClarificationView(BaseContestMixin, View):
  def send_notification_email(self, msg, recipients):
    send_mail(subject="Contest Question Notification", message=msg, from_email=None, recipient_list=recipients,
              fail_silently=True)

  def post(self, request, cid):
    text = request.POST.get("text", "")
    if not text or not request.user.is_authenticated:
      raise PermissionDenied
    if is_contest_manager(request.user, self.contest):
      ContestClarification.objects.create(contest=self.contest, important=True, author=request.user, answer=text)
      set_many_contest_notification([(self.contest.pk, user_id) for user_id in
                                     self.contest.contestparticipant_set.values_list("user_id", flat=True)])
    else:
      ContestClarification.objects.create(contest=self.contest, author=request.user, text=text)
      set_many_contest_notification([(self.contest.pk, user_id) for user_id in
                                     self.contest.managers.values_list("id", flat=True)])
    return redirect(reverse("contest:question", kwargs={"cid": self.contest.pk}))


class ContestClarificationAnswer(BaseContestMixin, View):

  def post(self, request, cid, pk):
    if is_contest_manager(request.user, self.contest):
      clarification = get_object_or_404(ContestClarification, contest_id=cid, pk=pk)
      builtin = request.POST.get("builtin", "custom")
      clarification.answer = request.POST.get("text", "")
      dfind = dict(BUILTIN_CHOICES)
      if builtin in dfind and builtin != "custom":
        clarification.answer = dfind[builtin]
      clarification.save(update_fields=["answer"])
      set_contest_notification(self.contest.pk, clarification.author_id)
      return redirect(reverse("contest:question", kwargs={"cid": self.contest.pk}))
    raise PermissionDenied
