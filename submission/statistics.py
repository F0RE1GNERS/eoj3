from random import uniform

from django.core.cache import cache

from submission.models import SubmissionStatus, Submission

USER_TOTAL_COUNT = 'u{user}_c{contest}_total_count'
USER_TOTAL_LIST = 'u{user}_c{contest}_total_list'
USER_AC_COUNT = 'u{user}_c{contest}_ac_count'
USER_AC_DIFF_COUNT = 'u{user}_c{contest}_ac_diff'
USER_AC_LIST = 'u{user}_c{contest}_ac_list'


def _get_or_invalidate(user_id, contest_id, cache_name):
    t = cache.get(cache_name)
    if t is None:
        update_user(user_id, contest_id)
        return cache.get(cache_name)
    else:
        return t


def get_accept_submission_count(user_id, contest_id=0):
    cache_name = USER_AC_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate(user_id, contest_id, cache_name)


def get_accept_problem_count(user_id, contest_id=0):
    cache_name = USER_AC_DIFF_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate(user_id, contest_id, cache_name)


def get_accept_problem_list(user_id, contest_id=0):
    cache_name = USER_AC_LIST.format(user=user_id, contest=contest_id)
    return _get_or_invalidate(user_id, contest_id, cache_name)


def get_total_submission_count(user_id, contest_id=0):
    cache_name = USER_TOTAL_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate(user_id, contest_id, cache_name)


def get_attempted_problem_list(user_id, contest_id=0):
    cache_name = USER_TOTAL_LIST.format(user=user_id, contest=contest_id)
    return _get_or_invalidate(user_id, contest_id, cache_name)


def invalidate_user(user_id, contest_id=0):
    cache.delete_many([USER_TOTAL_COUNT.format(user=user_id, contest=contest_id),
                       USER_TOTAL_LIST.format(user=user_id, contest=contest_id),
                       USER_AC_COUNT.format(user=user_id, contest=contest_id),
                       USER_AC_DIFF_COUNT.format(user=user_id, contest=contest_id),
                       USER_AC_LIST.format(user=user_id, contest=contest_id)])


def update_user(user_id, contest_id=0):
    cache_time = 300 * uniform(0.6, 1)
    if contest_id > 0:
        cache_time = 60 * uniform(0.6, 1)
        submission_filter = Submission.objects.filter(author_id=user_id, contest_id=contest_id).all()
    else:
        submission_filter = Submission.objects.filter(author_id=user_id).all()
    ac_filter = submission_filter.filter(status=SubmissionStatus.ACCEPTED).all()

    total_count = submission_filter.count()
    total_list = list(submission_filter.order_by().values_list("problem_id", flat=True).distinct())
    accept_count = ac_filter.count()
    accept_list = list(ac_filter.order_by().values_list("problem_id", flat=True).distinct())
    accept_diff = len(accept_list)

    cache.set(USER_TOTAL_COUNT.format(user=user_id, contest=contest_id), total_count, cache_time)
    cache.set(USER_TOTAL_LIST.format(user=user_id, contest=contest_id), total_list, cache_time)
    cache.set(USER_AC_COUNT.format(user=user_id, contest=contest_id), accept_count, cache_time)
    cache.set(USER_AC_DIFF_COUNT.format(user=user_id, contest=contest_id), accept_diff, cache_time)
    cache.set(USER_AC_LIST.format(user=user_id, contest=contest_id), accept_list, cache_time)
