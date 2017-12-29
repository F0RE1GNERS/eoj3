from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
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
    vector = SearchVector('title', weight='A') + SearchVector('description', weight='B') + \
             SearchVector('source', weight='B') + SearchVector('input', weight='C') + \
             SearchVector('output', weight='C')
    query = SearchQuery(q)
    weights = [0.1, 0.2, 0.4, 1.0]
    if is_admin_or_root(request.user):
        problems = Problem.objects.annotate(rank=SearchRank(vector, query, weights=weights)). \
                       filter(rank__gte=0.2, visible=True).order_by('-rank')[:LIMIT]
    else:
        problems = Problem.objects.annotate(rank=SearchRank(vector, query, weights=weights)). \
                       filter(rank__gte=0.2).order_by('-rank')[:LIMIT]
    # problems = [Problem.objects.get(pk=1)]
    # problems[0].rank = 0.9

    # query username
    users = User.objects.filter(username__icontains=q).extra(select={"rank": 0.8})[:LIMIT // 2]

    # query blogs
    vector = SearchVector('title', weight='A') + SearchVector('text', weight='B')
    blogs = Blog.objects.annotate(rank=SearchRank(vector, query, weights=[0.1, 0.2, 0.6, 1.0])). \
                filter(rank__gte=0.2, visible=True).order_by('-rank')[:LIMIT]
    # blogs = [Blog.objects.get(pk=1)]
    # blogs[0].rank = 1.0

    # query contests
    contests = Contest.objects.filter(title__icontains=q).extra(select={"rank": 0.7})[:LIMIT]

    LIMIT *= 2

    ctx["search_list"] = sorted(list(problems) + list(users) + list(blogs) + list(contests), key=lambda x: x.rank,
                                reverse=True)[:LIMIT]

    return render(request, 'search.jinja2', context=ctx)
