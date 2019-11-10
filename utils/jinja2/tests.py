from django_jinja import library

from account.permissions import is_admin_or_root


@library.test(name="admin")
def is_admin(user):
  return is_admin_or_root(user)
