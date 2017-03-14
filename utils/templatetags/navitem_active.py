from django import template
from django.core.urlresolvers import reverse, resolve

register = template.Library()

@register.simple_tag
def navitem_active(request, match):
    """
    In template: {% navitem_active request "namespace(optional):name" %}
    """
    resolve_path = resolve(request.path)
    print(resolve_path.namespace)

    if ':' in match:
        namespace, name = match.split(':', 1)
    else:
        namespace, name = '', match
    print(namespace, name)
    print(resolve_path.url_name)
    if resolve_path.namespace == namespace and resolve_path.url_name.startswith(name):
        return "active"
    return ""
