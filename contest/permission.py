from account.models import User
from account.permissions import is_admin_or_root
from .models import Contest


def has_permission_for_contest_management(user: User, contest: Contest):
    return user.is_authenticated and (is_admin_or_root(user) or contest.manager.filter(pk=user.pk).exists())
