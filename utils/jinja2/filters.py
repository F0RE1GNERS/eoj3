from django_jinja import library
import jinja2
from submission.models import STATUS_CHOICE


@library.filter(name='status_choice')
def status_choice(value):
    return dict(STATUS_CHOICE).get(value)


@library.filter(name='timedelta')
def timedelta_format(value):
    days, seconds = value.days, value.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    return "{:02}:{:02}".format(hours, minutes)
