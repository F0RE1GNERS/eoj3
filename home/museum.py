from datetime import datetime, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncYear
from django.shortcuts import render

from account.models import User
from dispatcher.manage import ping
from dispatcher.models import Server
from problem.models import Problem
from submission.models import Submission


def museum_view(request):
  def convert_timedelta(td):
    return {
      'year': td.days // 365,
      'day': td.days % 365,
      'hour': td.seconds // 3600,
      'minute': (td.seconds % 3600) // 60,
      'second': td.seconds % 60
    }

  ctx = {}
  ctx['total_problem_count'] = Problem.objects.count()
  ctx['total_submission_count'] = Submission.objects.count()
  ctx['total_user_count'] = User.objects.filter(is_active=True).count()
  # NOTE: this will break if there is no submission at all
  first_submission = Submission.objects.last()
  ctx['first_submission_time'] = first_submission.create_time
  ctx['first_submission_duration'] = convert_timedelta(datetime.now() - ctx['first_submission_time'])
  ctx['first_submission_author'] = first_submission.author

  from uptime import uptime
  ctx['uptime'] = convert_timedelta(timedelta(seconds=uptime()))
  ctx['server_time'] = datetime.now()
  ctx['eoj3_create_duration'] = convert_timedelta(datetime.now() - datetime(2017, 3, 11, 18, 32))

  ctx['submission_count_1'] = Submission.objects.filter(create_time__gt=datetime.now() - timedelta(days=1)).count()
  ctx['submission_count_7'] = Submission.objects.filter(create_time__gt=datetime.now() - timedelta(days=7)).count()
  ctx['submission_count_30'] = Submission.objects.filter(create_time__gt=datetime.now() - timedelta(days=30)).count()

  ctx['submission_stat'] = Submission.objects.filter(create_time__gt=datetime.today() - timedelta(days=30)). \
    annotate(date=TruncDate('create_time')).values('date'). \
    annotate(count=Count('id')).values('date', 'count').order_by()
  ctx['user_stat'] = User.objects.filter(is_active=True).annotate(date=TruncYear('date_joined')).values('date'). \
    annotate(count=Count('id')).values('date', 'count').order_by("date")
  for idx, user in enumerate(ctx['user_stat']):
    if idx == 0:
      continue
    user['count'] += ctx['user_stat'][idx - 1]['count']
  ctx['problem_stat'] = Problem.objects.annotate(date=TruncYear('create_time')).values('date'). \
    annotate(count=Count('id')).values('date', 'count').order_by("date")
  for idx, user in enumerate(ctx['problem_stat']):
    if idx == 0:
      continue
    user['count'] += ctx['problem_stat'][idx - 1]['count']

  ctx['servers'] = servers = Server.objects.filter(enabled=True)

  for server in servers:
    server.status = ping(server)

  return render(request, 'museum.jinja2', context=ctx)
