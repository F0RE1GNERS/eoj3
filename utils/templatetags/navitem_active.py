from django import template
from django.core.urlresolvers import reverse, resolve

register = template.Library()


@register.simple_tag(takes_context=True)
def navitem_active(context, match, **kwargs):
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
    if (not namespace or namespace in resolve_path.namespaces) and resolve_path.url_name.startswith(name):
        return "active"
    return ""
