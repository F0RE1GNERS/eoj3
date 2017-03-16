from django import template
from django.core.urlresolvers import reverse, resolve

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
    else:
        if resolve_path.url_name.startswith(match) and not resolve_path.namespace or resolve_path.namespace == match:
            return "active"
    return ""
