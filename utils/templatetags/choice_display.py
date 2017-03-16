from django import template
from submission.models import STATUS_CHOICE

register = template.Library()


@register.filter(name='status_choice')
def status_choice(value):
    return dict(STATUS_CHOICE).get(value)
