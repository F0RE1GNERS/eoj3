from django_jinja import library
import jinja2
from bs4 import BeautifulSoup
import markupsafe
from django.core.urlresolvers import reverse, resolve


@library.global_function(name='active')
@jinja2.contextfunction
def is_active(context, match, **kwargs):
    """
    In template: {% navitem_active "namespace(optional):name" %}
    For further usage, if you need something more specific, remember to parse all kwargs here.
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
