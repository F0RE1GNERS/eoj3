import os
from datetime import datetime

import jinja2
import markupsafe
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, Case, IntegerField, When
from django.http import QueryDict
from django_comments_xtd.templatetags.comments_xtd import XtdComment
from django_jinja import library

from utils.pagination import EndlessPaginator


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
            and (name == '*' or (resolve_path.url_name is not None and resolve_path.url_name.startswith(name))):
        return "active"
    return ""


@library.global_function(name='my_paginator')
@jinja2.contextfunction
@library.render_with("components/pagination.jinja2")
def paginator(context, adjacent_pages=3):
    display_pages = adjacent_pages * 2 + 1
    page_obj = context['page_obj']
    endless = isinstance(context['paginator'], EndlessPaginator)
    if endless:
        num = int(1e18)  # Hopefully we will get there!
    else:
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
        'endless': endless
    }


@library.global_function(name='render_comment_tree')
@jinja2.contextfunction
@library.render_with("comments/comment_tree.jinja2")
def render_comment_tree(context, obj):

    def tree_from_queryset(queryset, with_feedback=False, user=None):
        """Converts a XtdComment queryset into a list of nested dictionaries.
        The queryset has to be ordered by thread_id, order.
        Each dictionary contains two attributes::
            {
                'comment': the comment object itself,
                'children': [list of child comment dictionaries]
            }
        """
        def get_user_feedback(comment, user):
            d = {
                'likes_count': comment.likes__count,
                'dislikes_count': comment.dislikes__count,
                 }
            if user.is_authenticated:
                d['likes_flag'] = comment.likes__flag
            else:
                d['likes_flag'] = 0
            return d

        def add_children(children, obj, user):
            for item in children:
                if item['comment'].pk == obj.parent_id:
                    child_dict = {'comment': obj, 'children': []}
                    if with_feedback:
                        child_dict.update(get_user_feedback(obj, user))
                    item['children'].append(child_dict)
                    return True
                elif item['children']:
                    if add_children(item['children'], obj, user):
                        return True
            return False

        def get_new_dict(obj):
            new_dict = {'comment': obj, 'children': []}
            if with_feedback:
                new_dict.update(get_user_feedback(obj, user))
            return new_dict

        dic_list = []
        cur_dict = None
        for obj in queryset:
            if cur_dict and obj.level == cur_dict['comment'].level:
                dic_list.append(cur_dict)
                cur_dict = None
            if not cur_dict:
                cur_dict = get_new_dict(obj)
                continue
            if obj.parent_id == cur_dict['comment'].pk:
                child_dict = get_new_dict(obj)
                cur_dict['children'].append(child_dict)
            else:
                add_children(cur_dict['children'], obj, user)
        if cur_dict:
            dic_list.append(cur_dict)
        return dic_list

    def sort(c, sort_with_like, depth):
        def key(x):
            day = (datetime.now() - x['comment'].submit_date).seconds / 86400
            if sort_with_like:
                vote = x['likes_count'] - x['dislikes_count'] * 3
            else:
                vote = 0
            return vote - day
        c = sorted(c, key=key, reverse=True)
        if depth:
            for i in range(len(c)):
                if c[i]['children']:
                    c[i]['children'] = sort(c[i]['children'], sort_with_like, depth - 1)
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
    from django_comments_xtd.models import LIKEDIT_FLAG
    from django_comments_xtd.models import DISLIKEDIT_FLAG
    queryset = XtdComment.objects.filter(content_type=ctype,
                                         object_pk=obj.pk,
                                         site__pk=settings.SITE_ID,
                                         is_public=True).annotate(
        likes__count=Sum(Case(When(flags__flag=LIKEDIT_FLAG, then=1), default=0, output_field=IntegerField()))).annotate(
        dislikes__count=Sum(Case(When(flags__flag=DISLIKEDIT_FLAG, then=1), default=0, output_field=IntegerField())))
    user = context['user']
    if user.is_authenticated:
        queryset = queryset.annotate(
            likes__flag=Sum(Case(When(flags__user=user, flags__flag=LIKEDIT_FLAG, then=1),
                                 When(flags__user=user, flags__flag=DISLIKEDIT_FLAG, then=-1),
                                 default=0, output_field=IntegerField())))
    comments = tree_from_queryset(
        queryset,
        with_feedback=config['allow_feedback'],
        user=user
    )
    comments = sort(comments, sort_with_like=config['allow_feedback'], depth=2)
    ctx = dict(comments=comments, user=user)
    ctx.update(config)
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


@library.global_function(name='url_encode')
def url_encode(d):
    q = QueryDict(mutable=True)
    for key, val in d.items():
        q[key] = val
    return q.urlencode()


@library.global_function(name='static_file_modify')
def static_file_modify():
    def get_modified_time(path):
        return max(map(lambda x: int(os.path.getmtime(x[0])), os.walk(path)))
    t = cache.get("STATIC_FILE_MODIFIED_TIME")
    if t is None:
        t = max(map(get_modified_time, [os.path.join(settings.STATIC_DIR, "css"), os.path.join(settings.STATIC_DIR, "js")]))
        cache.set("STATIC_FILE_MODIFIED_TIME", t)
    return t


@library.global_function(name='username_display')
@jinja2.contextfunction
@library.render_with("components/username_display.jinja2")
def username_display(context, user, *args, **kwargs):
    legend = in_contest = False
    username = user.username
    if '#' in username:
        if username.endswith('old'):
            legend = True
            username = username[:-4]
        elif username.startswith('c'):
            pos = username.find('#')
            in_contest = username[1:pos]
            username = username[pos+1:]
    return {
        'color': user.magic,
        'user_id': user.pk,
        'username': username,
        'legend': legend,
        'in_contest': in_contest,
        'additional_class': kwargs.pop('additional_class', '')
    }