from datetime import datetime
from threading import Thread

import requests
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, reverse, redirect
from random import randint
from django.conf import settings

from os import path, listdir

from django_comments_xtd.models import XtdComment

from account.permissions import is_admin_or_root
from blog.models import Blog
from django.views.generic import TemplateView
from submission.statistics import get_accept_problem_count
from utils import random_string
from utils.site_settings import is_site_closed, site_settings_get
from utils.upload import save_uploaded_file_to


def file_manager(request):
    def slugify(text):
        import re
        return re.sub(r'[ /"#!:]+', '_', text)

    if not is_admin_or_root(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        try:
            file = request.FILES['file']
            save_uploaded_file_to(file, settings.UPLOAD_DIR, filename=slugify(file.name))
        except Exception as e:
            raise PermissionDenied(repr(e))
    return render(request, 'filemanager.jinja2', context={
        'file_list': list(map(lambda x: {
            'name': x,
            'modified_time': datetime.fromtimestamp(path.getmtime(path.join(settings.UPLOAD_DIR, x))).
                              strftime(settings.DATETIME_FORMAT_TEMPLATE),
            'size': str(path.getsize(path.join(settings.UPLOAD_DIR, x)) // 1024) + "K"
        }, filter(lambda x: path.isfile(path.join(settings.UPLOAD_DIR, x)), listdir(settings.UPLOAD_DIR))))
    })


def proxy_file_downloader(request):
    if not is_admin_or_root(request.user):
        raise PermissionDenied

    def download_file(url):
        local_filename = url.split('/')[-1]
        if local_filename == '':
            local_filename = random_string()
        r = requests.get(url, stream=True, timeout=30)
        with open(path.join(settings.UPLOAD_DIR, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    if request.method == 'POST':
        try:
            url = request.POST['url']
            Thread(target=download_file, args=(url,)).start()
        except Exception as e:
            raise PermissionDenied(repr(e))
    return redirect(reverse('filemanager'))


def home_view(request):
    if request.user.is_authenticated:
        ctx = {'solved': get_accept_problem_count(request.user.pk),
               'bulletin': site_settings_get('BULLETIN', '')}
        if not is_site_closed():
            LIMIT = 15
            ctx['blog_list'] = Blog.objects.with_likes().with_likes_flag(request.user).select_related(
                "author").order_by("-create_time").filter(visible=True, recommend=True)[:LIMIT]
            comment_list, blog_list = XtdComment.objects.order_by("-submit_date").select_related("user", "content_type").all()[:LIMIT],\
                                      Blog.objects.order_by("-create_time").select_related("author").filter(visible=True)[:LIMIT]
            ctx['comment_list'] = []
            i, j = 0, 0
            for k in range(LIMIT):
                if i < len(comment_list) and comment_list[i].submit_date > blog_list[j].create_time:
                    ctx['comment_list'].append(comment_list[i])
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
