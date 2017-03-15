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
    else:
        namespace, name = match, ''
    if resolve_path.namespace == namespace or resolve_path.url_name.startswith(namespace):
        return "active"
    return ""
