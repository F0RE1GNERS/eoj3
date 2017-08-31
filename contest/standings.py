from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.views import static

from .models import ContestParticipant
from .views import BaseContestMixin
from .statistics import get_contest_rank, get_participant_rank, invalidate_contest
from utils import xlsx_generator
from django.conf import settings


class ContestStandings(BaseContestMixin, ListView):
    template_name = 'contest/standings.jinja2'
    context_object_name = 'rank_list'

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get('privilege'):
            self.view_hidden = True
        return super(ContestStandings, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        if self.privileged and self.view_hidden:
            return None
        else:
            return 100

    def test_func(self):
        if self.privileged:
            return True
        if not self.contest.visible or self.contest.standings_disabled:
            return False
        if self.contest.standings_public and self.contest.status >= 0:
            return True
        return super(ContestStandings, self).test_func()

    def get_queryset(self):
        return get_contest_rank(self.contest, self.privileged and self.view_hidden)

    def get_context_data(self, **kwargs):
        data = super(ContestStandings, self).get_context_data(**kwargs)
        contest_participants = {user.user_id: user for user in
                                ContestParticipant.objects.filter(contest=self.contest).select_related('user',
                                                                                                       'contest').
                                    all()}
        for rank in data['rank_list']:
            rank.update(user=contest_participants[rank['user']])
        data['my_rank'] = get_participant_rank(self.contest, self.request.user.pk)
        print(data)
        return data


class ContestUpdateStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied('You cannot update the standings.')
        invalidate_contest(self.contest)
        return HttpResponseRedirect(reverse('contest:standings', kwargs={'cid': cid}))


class ContestDownloadStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied('You cannot download the standings.')
        file_name = xlsx_generator.generate(cid)
        return static.serve(request, file_name, document_root=settings.GENERATE_DIR)
