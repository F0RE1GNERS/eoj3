from datetime import datetime

from django.db.models import Q
from django.shortcuts import render

from account.models import User
from account.permissions import is_admin_or_root
from blog.models import Blog
from contest.models import Contest
from problem.models import Problem


def search_view(request):
    q = request.GET.get('q', '')
    if not q:
        return render(request, 'search.jinja2')
    ctx = {"q": q}
    LIMIT = 50

    # query problems
    query = Q(title__icontains=q) | Q(description__icontains=q) | Q(source__icontains=q) | Q(input__icontains=q) | Q(
        output__icontains=q)
    if is_admin_or_root(request.user):
        problems = Problem.objects.filter(query)
    else:
        problems = Problem.objects.filter(query, visible=True)
    weight_dict = {"title": 1.0, "description": 0.5, "source": 0.9, "input": 0.2, "output": 0.2}
    for problem in problems:
        problem.rank = 0.0
        for attr in weight_dict:
            if q in getattr(problem, attr):
                problem.rank += weight_dict[attr]

    # query username
    users = User.objects.filter(username__icontains=q)[:LIMIT // 2]
    for user in users:
        user.rank = 0.7 * (user.last_login - user.date_joined).total_seconds() / (
        datetime.now() - user.date_joined).total_seconds()

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
    contests = Contest.objects.filter(title__icontains=q).extra(select={"rank": 0.7})[:LIMIT]

    LIMIT *= 2

    ctx["search_list"] = sorted(list(problems) + list(users) + list(blogs) + list(contests), key=lambda x: x.rank,
                                reverse=True)[:LIMIT]

    return render(request, 'search.jinja2', context=ctx)
