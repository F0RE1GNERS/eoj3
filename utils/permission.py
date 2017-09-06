from account.permissions import is_admin_or_root

def has_permission_for_problem_management(user, problem):
    return user.is_authenticated and (is_admin_or_root(user) or problem.problemmanagement_set.filter(user=user).exists())


def has_permission_for_contest_management(user, contest):
    return user.is_authenticated and (is_admin_or_root(user) or contest.manager.filter(pk=user.pk).exists())


def get_permission_for_submission(user, submission, special_permission=False):
    if user.is_authenticated:
        if submission.contest and has_permission_for_contest_management(user, submission.contest):
            return 2
        if submission.problem and has_permission_for_problem_management(user, submission.problem):
            return 2
        if user == submission.author or special_permission:
            return 1
    return 0