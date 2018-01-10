from random import randint

from django.shortcuts import render
from django.views.generic import TemplateView
from django_comments_xtd.models import XtdComment

from blog.models import Blog
from submission.statistics import get_accept_problem_count
from utils.site_settings import is_site_closed, site_settings_get


def home_view(request):
    if request.user.is_authenticated:
        ctx = {'solved': get_accept_problem_count(request.user.pk),
               'bulletin': site_settings_get('BULLETIN', '')}
        if not is_site_closed():
            LIMIT, LIMIT_BLOG = 20, 15
            ctx['blog_list'] = Blog.objects.with_likes().with_likes_flag(request.user).select_related(
                "author").order_by("-create_time").filter(visible=True, recommend=True)[:LIMIT_BLOG]
            comment_list, blog_list = XtdComment.objects.filter(is_public=True, is_removed=False).order_by(
                "-submit_date").select_related("user", "content_type").prefetch_related('content_object').all()[:LIMIT], \
                                      Blog.objects.order_by("-create_time").select_related("author").filter(
                                          visible=True)[:LIMIT]
            ctx['comment_list'] = []
            i, j = 0, 0
            for k in range(LIMIT):
                if i < len(comment_list) and (j == len(blog_list) or (
                        j < len(blog_list) and comment_list[i].submit_date > blog_list[j].create_time)):
                    ctx['comment_list'].append(comment_list[i])
                    print(comment_list[i].__dict__)
                    i += 1
                elif j < len(blog_list):
                    ctx['comment_list'].append(blog_list[j])
                    j += 1
                else:
                    break
            for comment in ctx['comment_list']:
                if isinstance(comment, XtdComment) and len(comment.comment) > LIMIT:
                    comment.comment = comment.comment[:LIMIT] + '...'
        return render(request, 'home_logged_in.jinja2', context=ctx)
    else:
        return render(request, 'home.jinja2', context={'bg': '/static/image/bg/%d.jpg' % randint(1, 14), })


def forbidden_view(request, exception):
    return render(request, 'error/403.jinja2', context={"exception": exception})


def not_found_view(request):
    return render(request, 'error/404.jinja2')


def server_error_view(request):
    return render(request, 'error/500.jinja2')


def faq_view(request):
    return render(request, 'faq.jinja2')


class TestView(TemplateView):
    template_name = 'test.jinja2'
