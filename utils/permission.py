from account.permissions import is_admin_or_root

def is_problem_manager(user, problem):
    return user.is_authenticated and (is_admin_or_root(user) or problem.managers.filter(pk=user.pk).exists())


def is_contest_manager(user, contest):
    return user.is_authenticated and (is_admin_or_root(user) or contest.managers.filter(pk=user.pk).exists())


def get_permission_for_submission(user, submission, special_permission=False):
    if user.is_authenticated:
        if submission.contest and is_contest_manager(user, submission.contest):
            return 2
        if submission.problem and is_problem_manager(user, submission.problem):
            return 2
        if user == submission.author or special_permission:
            return 1
    return 0