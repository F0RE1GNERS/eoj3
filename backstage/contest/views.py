from threading import Thread

from django.contrib import messages
from django.db import transaction
from django.shortcuts import HttpResponse, get_object_or_404, redirect
from django.template import loader
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django_q.tasks import async_task

from account.color import update_color
from account.models import User
from backstage.models import Email
from contest.models import Contest, ContestUserRating
from contest.ratings import calculate_rating_changes, clear_previous_ratings
from utils.email import send_mail_with_bcc
from ..base_views import BaseBackstageMixin


class ContestList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 100
    context_object_name = 'contest_list'


class ContestApplyRatingChanges(BaseBackstageMixin, View):
    def post(self, request, cid):
        try:
            contest = get_object_or_404(Contest, pk=cid)
            if contest.access_level != 30:
                return HttpResponse()
            calculate_rating_changes(contest)
            messages.success(request, 'Ratings successfully updated.')
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponse()


class ContestWithdrawRatingChanges(BaseBackstageMixin, View):
    def post(self, request, cid):
        contest = get_object_or_404(Contest, pk=cid)
        clear_previous_ratings(contest)
        return HttpResponse()


class ApplyGlobalChangesToRating(BaseBackstageMixin, View):
    def post(self, request):
        user_ratings = {}

        with transaction.atomic():
            User.objects.all().update(rating=0)
            for rating in ContestUserRating.objects.select_related('user').all():
                if rating.user_id not in user_ratings:
                    user_ratings[rating.user_id] = rating
                    rating.user.rating = rating.rating
                    rating.user.save(update_fields=['rating'])

        update_color()
        return HttpResponse()
