from django.shortcuts import get_object_or_404
from django.utils.html import escape
from rest_framework.views import APIView
from rest_framework.response import Response
from tagging.models import Tag

from account.models import User
from blog.models import Blog
from contest.models import Contest, ContestParticipant
from problem.models import Problem
from account.permissions import is_admin_or_root

from django.db.models import Q
from django.urls import reverse

from functools import reduce
from operator import or_


def query_user(kw):
    results = list()
    if kw and len(kw) >= 3:
        for user in User.objects.filter(username__icontains=kw, is_active=True).exclude(username__icontains='#').\
                            all().only('username')[:5]:
            results.append(dict(title=escape(user.username), url=reverse('profile', kwargs=dict(pk=user.pk))))
    return dict(name='User', results=results)


def get_problem_q_object(kw, all=False, managing=None):
    if kw:
        q_list = list()
        if len(kw) >= 2:
            q_list.append(Q(title__icontains=kw))
            q_list.append(Q(alias__icontains=kw))
        if kw.isdigit():
            q_list.append(Q(pk__exact=kw))
        if q_list:
            q = reduce(or_, q_list)
            priv_list = list()
            if not all:
                priv_list.append(Q(visible=True))
                if managing:
                    priv_list.append(Q(managers=managing))
                q &= reduce(or_, priv_list)
            return q
    return None


def sorted_query(problems, kw):
    ret = {p.pk: 0.0 for p in problems}
    for p in problems:
        if str(p.pk) == kw:
            ret[p.pk] += 100
        if p.alias == kw:
            ret[p.alias] += 50
        if p.title == kw:
            ret[p.pk] += 30
    return sorted(problems, key=lambda p: ret[p.pk], reverse=True)[:5]


def query_problem(kw, all=False):
    results = list()
    q = get_problem_q_object(kw, all)
    if q:
        for problem in sorted_query(Problem.objects.defer("description", "input", "output", "hint").filter(q).distinct().all(), kw):
            results.append(dict(title=escape(problem.title),
                                url=reverse('problem:detail', kwargs=dict(pk=problem.pk))))
    return dict(name='Problem', results=results)


def query_blog(kw):
    results = list()
    if kw:
        for blog in Blog.objects.filter(title__icontains=kw, visible=True).all()[:5]:
            results.append(dict(title=escape(blog.title), url=reverse('blog:detail', kwargs={"pk": blog.pk})))
    return dict(name='Blog', results=results)


def query_contest(kw):
    results = list()
    if kw:
        for contest in Contest.objects.filter(title__icontains=kw, access_level__gt=0).all()[:5]:
            results.append(
                dict(title=escape(contest.title), url=reverse('contest:dashboard', kwargs={"cid": contest.pk})))
    return dict(name='Contest', results=results)


def query_tag(kw):
    results = list()
    if kw:
        for tag in Tag.objects.filter(name__icontains=kw).all()[:5]:
            results.append(dict(title=escape(tag.name), url=reverse('problem:list') + '?tag=%s' % tag.name))
    return dict(name='Tag', results=results)


class SearchAPI(APIView):
    def get(self, request):
        kw = request.GET.get('kw')
        results = dict()
        if kw:
            results['user'] = query_user(kw)
            results['problem'] = query_problem(kw, all=is_admin_or_root(request.user))
            results['tag'] = query_tag(kw)
            results['blog'] = query_blog(kw)
            results['contest'] = query_contest(kw)
            return Response(dict(results=results, action={
                "url": reverse('search') + '?q=%s' % kw,
                "text": "View all results"
            }))
        return Response(dict(results=results))


class SearchUserAPI(APIView):
    def get(self, request):
        kw = request.GET.get('kw')
        results = list()
        if kw:
            if 'contest' in request.GET and request.GET['contest'].isdigit():
                contest = request.GET['contest']
                query_from = get_object_or_404(Contest, pk=contest).participants.filter(username__icontains=kw)
            else:
                query_from = User.objects.filter(username__icontains=kw, is_active=True)
            for user in query_from.only('username', 'pk')[:5]:
                results.append(dict(name=user.username, value=user.pk))
        return Response(dict(success=True, results=results))


class SearchProblemAPI(APIView):
    def get(self, request):
        kw = request.GET.get('kw')
        managing = request.user if request.GET.get('managing') else None
        results = list()
        q = get_problem_q_object(kw, is_admin_or_root(request.user), managing)
        if q:
            for problem in sorted_query(Problem.objects.filter(q).distinct().all(), kw):
                results.append(dict(name=str(problem), value=problem.pk))
        return Response(dict(success=True, results=results))
