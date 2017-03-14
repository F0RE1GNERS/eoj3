from django import template
from django.core.urlresolvers import reverse, resolve

register = template.Library()

@register.simple_tag(takes_context=True)
def navitem_active(context, match):
    """
    In template: {% navitem_active "namespace(optional):name" %}
    """
    resolve_path = context['request'].resolver_match
    print(resolve_path.namespace)

    if ':' in match:
        namespace, name = match.split(':', 1)
    else:
        namespace, name = '', match
    if resolve_path.namespace == namespace and resolve_path.url_name.startswith(name):
        return "active"
    return ""
