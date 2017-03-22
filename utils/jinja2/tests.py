from django_jinja import library
import jinja2
from account.models import Privilege


@library.test(name="admin")
def is_admin(user):
    return user.is_authenticated and user.privilege in (Privilege.ROOT, Privilege.ADMIN)
