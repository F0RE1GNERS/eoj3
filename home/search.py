import time
from datetime import datetime

from django.db.models import Q
from django.shortcuts import render

from account.models import User
from account.permissions import is_admin_or_root
from blog.models import Blog
from contest.models import Contest
from problem.models import Problem


def search_view(request):
  q = request.GET.get('q', '').strip()
  if not q:
    return render(request, 'search.jinja2')
  ctx = {"q": q}
  LIMIT = 50

  start_time = time.time()

  # query problems
  query = Q(title__icontains=q) | Q(description__icontains=q) | Q(source__icontains=q) | Q(input__icontains=q) | Q(
    output__icontains=q)
  if q.isdigit():
    query |= Q(pk__exact=q)
  if is_admin_or_root(request.user):
    problems = Problem.objects.filter(query)
  else:
    problems = Problem.objects.filter(query, visible=True)
  weight_dict = {"title": 1.0, "description": 0.5, "source": 0.9, "input": 0.2, "output": 0.2}
  for problem in problems:
    problem.rank = 0.0
    for attr in weight_dict:
      if attr == "pk":
        if q == str(problem.pk):
          problem.rank += 5.0
      elif q in getattr(problem, attr):
        problem.rank += weight_dict[attr]

  # query username
  users = User.objects.filter(username__icontains=q, is_active=True)[:LIMIT // 2]
  for user in users:
    if user.last_login:
      user.rank = 0.7 * (user.last_login - user.date_joined).total_seconds() / (
        datetime.now() - user.date_joined).total_seconds()
    else:
      user.rank = 0.0

  # query blogs
  query = Q(title__icontains=q) | Q(text__icontains=q)
  blogs = Blog.objects.filter(query, visible=True).select_related("author")
  weight_dict = {"title": 1.0, "text": 0.6}
  for blog in blogs:
    blog.rank = 0.0
    for attr in weight_dict:
      if q in getattr(blog, attr):
        blog.rank += weight_dict[attr]

  # query contests
  contests = Contest.objects.filter(title__icontains=q, access_level__gt=0).extra(select={"rank": 0.7})[:LIMIT]

  LIMIT *= 2

  ctx["search_list"] = sorted(list(problems) + list(users) + list(blogs) + list(contests), key=lambda x: x.rank,
                              reverse=True)[:LIMIT]

  stop_time = time.time()
  ctx["query_time"] = '%.3f' % (stop_time - start_time)

  return render(request, 'search.jinja2', context=ctx)
