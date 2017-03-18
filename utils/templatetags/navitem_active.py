from django import template
from django.core.urlresolvers import reverse, resolve
from django.shortcuts import reverse
from django.utils.html import format_html
register = template.Library()


@register.simple_tag(takes_context=True)
def navitem_active(context, match):
    """
    In template: {% navitem_active "namespace:name(optional)" %}
    """
    resolve_path = context['request'].resolver_match
    if ':' in match:
        namespace, name = match.split(':', 1)
        if resolve_path.namespace == namespace and resolve_path.url_name.startswith(name):
            return "active"
    elif '/' in match:
        if context['request'].path == match:
            return "active"
    elif resolve_path.url_name.startswith(match) and not resolve_path.namespace or resolve_path.namespace == match:
            return "active"
    else:
        return ""


@register.simple_tag(takes_context=True)
def link_active(context, view_name, text, *args, **kwargs):
    if kwargs.pop('outside', None):
        html = r"""
            <li class="nav-item {active}">
                <a class="nav-link" href="{url}">{text}</a>
            </li>
            """
    else:
        html = '<a href="{url}" class="{active}">{text}</a>'
    active = False
    resolve_path = context['request'].resolver_match
    url = reverse(view_name, args=args)
    if args:
        if url == context['request'].path:
            active = True
    else:
        if ':' in view_name:
            namespace, name = view_name.split(':', 1)
            if resolve_path.namespace == namespace and resolve_path.url_name.startswith(name):
                active = True
        elif '/' in view_name:
            if context['request'].path == view_name:
                active = True
        elif resolve_path.url_name.startswith(view_name) and not resolve_path.namespace or resolve_path.namespace == view_name:
                active = True
    return format_html(html, url=url, active="active" if active else "", text=text)
