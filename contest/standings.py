import zipfile

from django.shortcuts import render, HttpResponseRedirect, reverse
from django.views.generic.list import ListView
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.views import static
from os import path

from problem.statistics import get_contest_problem_ac_submit
from submission.models import SubmissionStatus
from utils import random_string
from utils.language import LANG_EXT
from .models import ContestParticipant
from .views import BaseContestMixin
from .statistics import get_contest_rank, get_participant_rank, invalidate_contest, get_first_yes
from utils.csv_writer import write_csv
from utils.download import respond_generate_file
from django.conf import settings


class ContestStandings(BaseContestMixin, ListView):
    template_name = 'contest/standings.jinja2'
    context_object_name = 'rank_list'

    def dispatch(self, request, *args, **kwargs):
        self.view_hidden = bool(request.GET.get('privilege'))
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
        if not self.contest.standings_without_problem:
            data['statistics'] = {
                'problem': get_contest_problem_ac_submit(list(map(lambda x: x.problem_id,
                                                                  self.contest.contest_problem_list)),
                                                         self.contest.pk),
                'first_yes': get_first_yes(self.contest)
            }
        return data


class ContestUpdateStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied
        invalidate_contest(self.contest)
        return HttpResponseRedirect(reverse('contest:standings', kwargs={'cid': cid}))


class ContestDownloadStandings(BaseContestMixin, View):
    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied
        rank_list = get_contest_rank(self.contest)
        contest_participants = {user.user_id: user for user in
                                ContestParticipant.objects.filter(contest=self.contest).select_related('user',
                                                                                                       'contest').
                                    all()}

        header = ["Rank", "Username", "Info", "Score"]
        if self.contest.penalty_counts:
            header.append("Penalty")
        for problem in self.contest.contest_problem_list:
            header.append(problem.identifier)
        data = [header]
        for rank in rank_list:
            d = []
            d.append(str(rank["rank"]) if "rank" in rank else "*")
            participant = contest_participants[rank['user']]
            d.append(participant.user.username)
            d.append(participant.comment)
            d.append(str(rank["score"]))
            if self.contest.penalty_counts:
                d.append(str(rank["penalty"] // 60))
            for problem in self.contest.contest_problem_list:
                detail = rank["detail"].get(problem.problem_id)
                text = ''
                if detail and not detail.get("waiting", False) and detail.get("attempt"):
                    if self.contest.scoring_method != "acm":
                        text = str(detail["score"])
                    elif detail["solved"]:
                        text = "+" + str(detail["attempt"] - 1)
                        if self.contest.always_running:
                            text += '(%s)' % (detail["pass_time"])
                        elif self.contest.penalty_counts:
                            text += "(%d)" % (detail["time"] // 60)
                    else:
                        text = "-" + str(detail["attempt"])
                d.append(text)
            data.append(d)
        file_name = write_csv(data)
        return respond_generate_file(request, file_name, file_name_serve_as="ContestStandings - %s.csv" % self.contest.title)


class ContestDownloadCode(BaseContestMixin, View):
    @staticmethod
    def slugify_filename(string):
        for c in r' []/\;,><&*:%=+@!#^()|?^':
            string = string.replace(c, '_')
        return string

    def test_func(self):
        return super().test_func() and self.user.is_authenticated

    def get(self, request, cid):
        type = request.GET.get('t')
        if type and 'all' in type and self.privileged:
            submissions = self.contest.submission_set
        else:
            submissions = self.contest.submission_set.filter(author=request.user)
        if type and 'accepted' in type:
            submissions = submissions.filter(status=SubmissionStatus.ACCEPTED)
        submissions = submissions.select_related("author")
        self.contest.add_contest_problem_to_submissions(submissions)
        participants = dict(self.contest.contestparticipant_set.values_list('user_id', 'comment'))

        file_path = path.join(settings.GENERATE_DIR, random_string())
        lang_ext_dict = dict(LANG_EXT)
        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip:
            zip.writestr('/contest.nfo', '')
            for submission in submissions:
                user = submission.author.username
                if participants[submission.author_id]:
                    user = participants[submission.author_id]
                user = self.__class__.slugify_filename(user)
                if getattr(submission, 'contest_problem') and submission.contest_problem:
                    zip.writestr("/%s_%s/%s_#%d_%s.%s" % (user, submission.author_id, submission.contest_problem.identifier,
                                                          submission.pk, submission.get_status_display().replace(' ', '_'),
                                                          lang_ext_dict.get(submission.lang, 'txt')),
                                 submission.code)
        return respond_generate_file(request, file_path, "ContestCode - %s.zip" % self.contest.title)
