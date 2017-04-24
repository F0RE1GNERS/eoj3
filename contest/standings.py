from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.views import static

from .views import BaseContestMixin
from .models import Contest
from .tasks import update_contest
from account.permissions import is_admin_or_root
from utils import xlsx_generator
from eoj3.settings import GENERATE_DIR


class ContestStandings(BaseContestMixin, ListView):
    template_name = 'contest/standings.jinja2'
    paginate_by = 100
    context_object_name = 'rank_list'

    def test_func(self):
        if self.privileged:
            return True
        if not self.contest.visible:
            return False
        if self.contest.standings_public and self.contest.get_status() != 'pending':
            return True
        return super(ContestStandings, self).test_func()

    def get_queryset(self):
        return self.contest.contestparticipant_set.select_related('user').only('user_id', 'user__username', 'user__magic',
                                                                               'comment', 'contest_id', 'score', 'penalty',
                                                                               'html_cache', 'rank', 'star', 'user__nickname').all()

    def get_context_data(self, **kwargs):
        data = super(ContestStandings, self).get_context_data(**kwargs)
        try:
            data['my_rank'] = self.contest.contestparticipant_set.get(user=self.request.user).rank
        except:
            data['my_rank'] = 'N/A'
        data['update_time'] = self.contest.standings_update_time
        return data


class ContestUpdateStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied('You cannot update the standings.')
        update_contest(self.contest)
        return HttpResponseRedirect(reverse('contest:standings', kwargs={'cid': cid}))


class ContestDownloadStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied('You cannot download the standings.')
        file_name = xlsx_generator.generate(cid)
        return static.serve(request, file_name, document_root=GENERATE_DIR)
