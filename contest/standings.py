import zipfile
from collections import Counter

from django.http import HttpResponse
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
        return get_contest_rank(self.contest)

    def get_context_data(self, **kwargs):
        data = super(ContestStandings, self).get_context_data(**kwargs)
        contest_participants = {user.user_id: user for user in
                                ContestParticipant.objects.filter(contest=self.contest).select_related('user').
                                    all()}
        for rank in data['rank_list']:
            rank.update(user=contest_participants[rank['user']])
        # print(data['rank_list'])
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
            d.append(str(rank["actual_rank"]) if rank.get("actual_rank") else "")
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


class ContestStandingsTestSys(BaseContestMixin, View):

    def get_line(self, label, *args):
        print(args)
        s = []
        for x in args:
            xstr = str(x)
            if ' ' in xstr or ',' in xstr:
                s.append('"' + xstr + '"')
            else:
                s.append(xstr)
        return "@" + label + " " + ",".join(s)

    def get(self, request, cid):
        if not self.privileged:
            raise PermissionDenied
        head = ['']
        head.append(self.get_line('contest', self.contest.title))
        head.append(self.get_line('contlen', int((self.contest.end_time - self.contest.start_time).total_seconds() / 60)))
        head.append(self.get_line('problems', self.contest.contestproblem_set.count()))
        probs = [self.get_line('p', p.identifier, p.problem.title, 20, 0) for p in self.contest.contest_problem_list]
        available_prob_ids = set(map(lambda x: x.problem_id, self.contest.contest_problem_list))
        teams = []
        team_counter = 0
        team_mapper = dict()
        for participant in self.contest.contestparticipant_set.select_related("user").all():
            if participant.comment:
                name = participant.comment
            else:
                name = participant.user.username
            if self.contest.submission_set.filter(author_id=participant.user_id).exists():
                team_counter += 1
                teams.append(self.get_line('t', team_counter, 0, 1, name))
                team_mapper[participant.user_id] = team_counter
        subs = []
        sub_counter = Counter()
        sub_verdict_converter = {
            SubmissionStatus.ACCEPTED: "OK",
            SubmissionStatus.WRONG_ANSWER: "WA",
            SubmissionStatus.RUNTIME_ERROR: "RT",
            SubmissionStatus.TIME_LIMIT_EXCEEDED: "TL",
            SubmissionStatus.MEMORY_LIMIT_EXCEEDED: "ML",
            SubmissionStatus.COMPILE_ERROR: "CE",
        }
        for s in self.contest.submission_set.order_by("create_time").all():
            if s.problem_id in available_prob_ids:
                subs.append(self.get_line('s', team_mapper[s.author_id],
                                          self.contest.get_contest_problem(s.problem_id).identifier,
                                          sub_counter[(s.author_id, s.problem_id)] + 1,
                                          max(int((s.create_time - self.contest.start_time).total_seconds()), 0),
                                          sub_verdict_converter[s.status] if s.status in sub_verdict_converter else "RJ"))
                sub_counter[(s.author_id, s.problem_id)] += 1
        head.append(self.get_line("teams", len(teams)))
        head.append(self.get_line("submissions", len(subs)))
        return HttpResponse('\n'.join(head + probs + teams + subs), content_type='text/plain')
