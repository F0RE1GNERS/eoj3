from django import template

register = template.Library()


@register.filter(name='range')
def times(first, last):
    return range(first, last+1)