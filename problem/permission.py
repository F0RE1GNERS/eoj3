from account.models import User
from account.permissions import is_admin_or_root
from problem.models import Problem


def has_permission_for_problem_management(user: User, problem: Problem):
    return is_admin_or_root(user) or problem.problemmanagement_set.filter(user=user).exists()

