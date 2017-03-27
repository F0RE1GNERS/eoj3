from account.models import Privilege


def is_admin_or_root(user):
    return user.is_authenticated and user.privilege in (Privilege.ROOT, Privilege.ADMIN)