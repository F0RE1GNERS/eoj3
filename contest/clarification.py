from threading import Thread

from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.shortcuts import reverse, redirect, get_object_or_404
from django.views.generic import View
from django.utils.translation import ugettext_lazy as _
from notifications.signals import notify

from utils.permission import is_contest_manager
from .models import ContestClarification
from .views import BaseContestMixin


class ContestClarificationView(BaseContestMixin, View):
    def send_notification_email(self, msg, recipients):
        send_mail(subject="Contest Question Notification", message=msg, from_email=None, recipient_list=recipients,
                  fail_silently=True)

    def post(self, request, cid):
        if self.contest.status != 0:
            raise PermissionDenied
        text = request.POST.get("text", "")
        if not text or not request.user.is_authenticated:
            raise PermissionDenied
        if is_contest_manager(request.user, self.contest):
            ContestClarification.objects.create(contest=self.contest, important=True, author=request.user, answer=text)
            notify.send(sender=request.user,
                        recipient=list(map(lambda x: x.user, self.contest.contestparticipant_set.select_related("user").all())),
                        verb="posted a notification in",
                        level="warning",
                        target=self.contest,
                        description=text)
        else:
            ContestClarification.objects.create(contest=self.contest, author=request.user, text=text)
            notify.send(sender=request.user,
                        recipient=self.contest.managers.all(),
                        verb="asked a question in",
                        level="warning",
                        target=self.contest,
                        description=text)
            emails = self.contest.managers.all().values_list("email", flat=True)
            msg_pre = ["Contest: " + self.contest.title,
                       "Who: " + request.user.username,
                       "Question: " + text]
            Thread(target=self.send_notification_email, args=('\n'.join(msg_pre), list(emails))).start()
        return redirect(reverse("contest:dashboard", kwargs={"cid": self.contest.pk}))


class ContestClarificationAnswer(BaseContestMixin, View):

    def post(self, request, cid, pk):
        if is_contest_manager(request.user, self.contest):
            clarification = get_object_or_404(ContestClarification, contest_id=cid, pk=pk)
            clarification.answer = request.POST["text"]
            clarification.save(update_fields=["answer"])
            notify.send(sender=request.user,
                        recipient=[clarification.author],
                        verb="answered your question in",
                        level="warning",
                        target=self.contest,
                        description=clarification.answer)
            return redirect(reverse("contest:dashboard", kwargs={"cid": self.contest.pk}))
        raise PermissionDenied
