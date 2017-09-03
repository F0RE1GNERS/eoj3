import os
from datetime import datetime

import jinja2
import markupsafe
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django_comments_xtd.templatetags.comments_xtd import XtdComment
from django_jinja import library


@library.global_function(name='active')
@jinja2.contextfunction
def is_active(context, match, **kwargs):
    """
    In template: {{ active("namespace(optional):name") }}
    For further usage, if you need something more specific, remember to parse all kwargs here.

    Example:
        active("contest:*")  turn on for all pages in contest namespace
        active("problem:title")  turn on for all pages in problem and with the name "starts with" title

    """
    def check_kwargs(a, b):
        if len(a.items()) != len(b.items()):
            return False
        for (key, item) in a.items():
            try:
                check = b[key]
                # Ignore the type difference
                if str(check) != str(item):
                    return False
            except KeyError:
                return False
        return True

    resolve_path = context['request'].resolver_match
    if not resolve_path:
        return ""
    if kwargs and not check_kwargs(kwargs, resolve_path.kwargs):
        return ""
    (namespace, name) = match.split(':', 1) if ':' in match else ('', match)
    if ((not namespace and not resolve_path.namespaces) or namespace in resolve_path.namespaces) \
            and (name == '*' or resolve_path.url_name.startswith(name)):
        return "active"
    return ""


@library.global_function(name='my_paginator')
@jinja2.contextfunction
@library.render_with("components/pagination.jinja2")
def paginator(context, adjacent_pages=3):
    display_pages = adjacent_pages * 2 + 1
    page_obj = context['page_obj']
    num = context['paginator'].num_pages
    cur = page_obj.number
    if num <= display_pages:
        page_numbers = range(1, num + 1)
    elif cur - adjacent_pages <= 1:
        page_numbers = range(1, display_pages + 1)
    elif cur + adjacent_pages >= num:
        page_numbers = range(num - display_pages + 1, num + 1)
    else:
        page_numbers = range(cur - adjacent_pages, cur + adjacent_pages + 1)
    return {
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'request': context['request'],
    }


@library.global_function(name='render_comment_tree')
@jinja2.contextfunction
@library.render_with("comments/comment_tree.jinja2")
def render_comment_tree(context, obj):
    def sort(c, depth):
        def key(x):
            day = (datetime.now() - x['comment'].submit_date).seconds / 86400
            vote = len(x['likedit_users']) - len(x['dislikedit_users']) * 3
            return vote - day
        c = sorted(c, key=key, reverse=True)
        if depth:
            for i in range(len(c)):
                if c[i]['children']:
                    c[i]['children'] = sort(c[i]['children'], depth - 1)
        return c

    def get_config(content_type):  # from django_comments_xtd.utils
        _default = {
            'allow_flagging': False,
            'allow_feedback': False,
            'show_feedback': False
        }
        key = "%s.%s" % (content_type.app_label, content_type.model)
        try:
            return settings.COMMENTS_XTD_APP_MODEL_OPTIONS[key]
        except KeyError:
            return settings.COMMENTS_XTD_APP_MODEL_OPTIONS.setdefault(
                'default', _default)

    ctype = ContentType.objects.get_for_model(obj)
    config = get_config(ctype)
    queryset = XtdComment.objects.filter(content_type=ctype,
                                         object_pk=obj.pk,
                                         site__pk=settings.SITE_ID,
                                         is_public=True)
    comments = XtdComment.tree_from_queryset(
        queryset,
        with_flagging=config['allow_flagging'],
        with_feedback=config['allow_feedback'],
        user=context['user']
    )
    if config['allow_feedback']:
        comments = sort(comments, depth=1)
    ctx = dict(comments=comments, user=context['user'])
    ctx.update(config)
    # print(ctx)
    # print(config)
    return ctx


@library.global_function(name='render_field')
def render_field(field, attrs):
    add_attrs = attrs or {}
    soup = BeautifulSoup(str(field), "html.parser")
    soup.contents[0].attrs.update(add_attrs)
    return markupsafe.Markup(soup)


@library.global_function(name='url_replace')
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@library.global_function(name='static_file_modify')
def static_file_modify(path):
    real_path = os.path.join(settings.STATIC_DIR, path)
    return int(os.path.getmtime(real_path))