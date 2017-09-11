from django.shortcuts import HttpResponseRedirect, reverse, redirect, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic import View
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
import json
import datetime

from utils.permission import has_permission_for_contest_management
from .models import Contest, ContestClarification
from .views import BaseContestMixin
from account.permissions import is_admin_or_root


class ContestClarificationView(BaseContestMixin, View):

    def post(self, request, cid):
        if self.contest.status != 0:
            raise PermissionDenied
        text = request.POST["text"]
        if not text:
            raise PermissionDenied
        if has_permission_for_contest_management(request.user, self.contest):
            ContestClarification.objects.create(contest=self.contest, important=True, author=request.user, answer=text)
        else:
            ContestClarification.objects.create(contest=self.contest, author=request.user, text=text)
        return redirect(reverse("contest:dashboard", kwargs={"cid": self.contest.pk}))


class ContestClarificationAnswer(BaseContestMixin, View):

    def post(self, request, cid, pk):
        if has_permission_for_contest_management(request.user, self.contest):
            clarification = get_object_or_404(ContestClarification, contest_id=cid, pk=pk)
            clarification.answer = request.POST["text"]
            clarification.save(update_fields=["answer"])
            return redirect(reverse("contest:dashboard", kwargs={"cid": self.contest.pk}))
        raise PermissionDenied
