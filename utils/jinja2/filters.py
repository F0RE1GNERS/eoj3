from django_jinja import library
import jinja2
from submission.models import STATUS_CHOICE


@library.filter(name='status_choice')
def status_choice(value):
    return dict(STATUS_CHOICE).get(value)
