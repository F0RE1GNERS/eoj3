from django.shortcuts import HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic import View
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.contrib import messages
import json
import datetime

from .models import Contest, ContestClarification
from .views import BaseContestMixin
from account.permissions import is_admin_or_root


class ContestClarificationView(BaseContestMixin, ListView):
    template_name = 'contest/clarification.jinja2'
    context_object_name = 'clarification_list'

    def get_queryset(self):
        cmp = dict(note=-1, open=0, close=1, solve=1)
        return sorted(Contest.objects.get(pk=self.kwargs.get('cid')).contestclarification_set.all(),
                      key=lambda x: cmp[x.status])

    def post(self, request, cid):
        contest = Contest.objects.get(pk=cid)
        if timezone.now() < contest.start_time or timezone.now() > contest.end_time:
            messages.error(self.request, 'You are currently not in the period of the contest.')
            return HttpResponseRedirect(self.request.path)

        if is_admin_or_root(request.user):
            status = 'note'
        else:
            status = 'open'
        ContestClarification.objects.create(contest_id=self.kwargs['cid'], author=request.user,
                                            text=request.POST['message'], status=status)
        return HttpResponseRedirect(request.POST['next'])


class ContestClarificationToggle(BaseContestMixin, View):
    def get(self, request, cid, clarification_id, operation):
        if not is_admin_or_root(request.user):
            raise PermissionDenied("You don't have the access.")
        if operation != 'close' and operation != 'solve':
            raise PermissionDenied("Bad operation code.")
        clarification = ContestClarification.objects.get(pk=clarification_id)
        clarification.status = operation
        clarification.save(update_fields=["status"])
        return HttpResponseRedirect(reverse('contest:clarification', kwargs={'cid': cid}))


class ContestClarificationQuery(BaseContestMixin, View):
    def get(self, request, cid):
        contest = Contest.objects.get(pk=cid)
        data = {"time": timezone.now().timestamp()}
        try:
            time = datetime.datetime.fromtimestamp(float(request.GET["time"]))
            if is_admin_or_root(request.user):
                response = contest.contestclarification_set.filter(status='open', time__gt=time).all()
                data['type'] = 'New Question:<br><br>'
            else:
                response = contest.contestclarification_set.filter(status='note', time__gt=time).all()
                data['type'] = 'New Clarification:<br><br>'
            data['response'] = '<br><br>----------<br><br>'.join(map(lambda x: str(x).strip().replace('\n', '<br>'), response))
            if contest.get_status() != 'running':
                data['response'] = 'reject'
        except Exception as e:
            # print(repr(e))
            pass
        return HttpResponse(json.dumps(data))