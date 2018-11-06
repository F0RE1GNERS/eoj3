import calendar
import json
from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from account.models import User
from blog.models import Blog
from contest.models import ContestUserRating
from contest.statistics import get_participant_rank
from problem.statistics import get_accept_problem_count
from submission.models import SubmissionStatus


class ProfileView(TemplateView):
    template_name = 'profile.jinja2'

    def get_recent_blogs(self):
        return self.user.blog_set.filter(visible=True).order_by("-edit_time")[:5]

    def get_recent_contests(self):
        ret = self.user.contestparticipant_set.select_related("contest").filter(contest__access_level__gt=0,
                                                                                contest__common_status_access_level__gte=0,
                                                                                contest__contest_type=0,
                                                                                star=False). \
                   order_by("-contest__start_time")[:5]
        for cp in ret:
            if not cp.star:
                cp.rank = get_participant_rank(cp.contest, self.user.id)
        return ret

    def get_recent_gyms(self):
        ret = self.user.contestparticipant_set.select_related("contest").filter(contest__access_level__gt=0,
                                                                                contest__contest_type=1). \
                   order_by("-contest__create_time")[:5]
        for cp in ret:
            try:
                cp.last_submission = cp.contest.submission_set.filter(author=self.user).first()
            except:
                cp.last_submission = None
        return ret

    def get_recent_solved_problems(self):
        ret, accepted_problems = [], set()
        for sub in self.user.submission_set.filter(status=SubmissionStatus.ACCEPTED, problem__visible=True).select_related("problem"):
            if sub.problem_id not in accepted_problems:
                accepted_problems.add(sub.problem_id)
                ret.append(sub)
                if len(ret) >= 10:
                    break
        return ret

    def get_rating_changes(self):
        return ContestUserRating.objects.filter(user=self.user).select_related("contest").order_by("modified")

    def get_heatmap_data(self):
        now = datetime.now()
        one_year_ago = now.replace(year=now.year - 1, hour=0, minute=0, second=0, microsecond=0)
        query_ret = self.user.submission_set.filter(create_time__gte=one_year_ago). \
                annotate(date=TruncDay('create_time')).values("date").order_by("date").annotate(count=Count('id'))
        min_date = one_year_ago - timedelta(days=1)
        stat_dict = dict()
        last_week_set, last_day_set = set(), set()
        while min_date < now:
            stat_dict[min_date] = 0
            last_day = calendar.monthrange(min_date.year, min_date.month)[1]
            if min_date.day > last_day - 7:
                last_week_set.add(min_date)
            if min_date.day > last_day - 1:
                last_day_set.add(min_date)
            min_date += timedelta(days=1)
        for r in query_ret:
            stat_dict[r["date"]] += r["count"]

        ret = []
        week_number_dict = dict()
        week_to_month = dict()
        for r in sorted(stat_dict.items(), key=lambda r: r[0]):
            year, weeknumber, weekday = r[0].isocalendar()
            if (year, weeknumber) not in week_number_dict:
                sz = len(week_number_dict)
                week_number_dict[(year, weeknumber)] = sz + 1
            weeknumber = week_number_dict[(year, weeknumber)]
            if r[0].day == 10:
                week_to_month[weeknumber] = r[0].month
            ret.append({"date": r[0].strftime("%Y-%m-%d"),
                        "lastWeek": r[0] in last_week_set, "lastDay": r[0] in last_day_set,
                        "year": year, "week": weeknumber, "day": weekday - 1, "submissions": r[1]})
        return json.dumps(ret), json.dumps(week_to_month)

    def get_solved(self):
        return get_accept_problem_count(self.user.id)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        try:
            data['profile'] = self.user = User.objects.get(pk=self.kwargs['pk'], is_active=True)
        except:
            raise Http404
        data['blogs'] = self.get_recent_blogs()
        data['contests'] = self.get_recent_contests()
        data['gyms'] = self.get_recent_gyms()
        data['submissions'] = self.get_recent_solved_problems()
        data['rating_changes'] = self.get_rating_changes()
        data['max_rating'], data['min_rating'] = 1800, 1200
        if data['rating_changes']:
            data['max_rating'] = max(data['max_rating'], max(map(lambda x: x.rating, data['rating_changes'])))
            data['min_rating'] = min(data['min_rating'], max(map(lambda x: x.rating, data['rating_changes'])))
        data['heatmap'], data['week_to_month'] = self.get_heatmap_data()
        data['solved'] = self.get_solved()
        return data
