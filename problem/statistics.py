from random import uniform

from django.core.cache import cache

from submission.models import SubmissionStatus, Submission

PROBLEM_AC_USER_COUNT = 'p{problem}_c{contest}_ac_user_count'
PROBLEM_ALL_USER_COUNT = 'p{problem}_c{contest}_all_user_count'
PROBLEM_AC_USER_RATIO = 'p{problem}_c{contest}_ac_ratio_user'
PROBLEM_AC_COUNT = 'p{problem}_c{contest}_ac_count'
PROBLEM_ALL_COUNT = 'p{problem}_c{contest}_all_count'
PROBLEM_AC_RATIO = 'p{problem}_c{contest}_ac_ratio'


def _get_or_invalidate(problem_id, contest_id, cache_name):
    t = cache.get(cache_name)
    if t is None:
        invalidate_problem(problem_id, contest_id)
        return cache.get(cache_name)
    else:
        return t


def get_problem_accept_user_count(problem_id, contest_id=0):
    """
    get problem accept count (user), with cache

    :type problem_id: int
    :return:
    """
    return get_many_problem_accept_count([problem_id], contest_id)[problem_id]


def get_problem_all_user_count(problem_id, contest_id=0):
    cache_name = PROBLEM_ALL_USER_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_user_ratio(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_USER_RATIO.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_count(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_all_count(problem_id, contest_id=0):
    cache_name = PROBLEM_ALL_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_ratio(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_RATIO.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_many_problem_accept_count(problem_ids, contest_id=0):
    cache_res = cache.get_many(list(map(lambda x: PROBLEM_AC_USER_COUNT.format(problem=x, contest=contest_id),
                                        problem_ids)))
    ans = dict()
    for problem_id in problem_ids:
        cache_name = PROBLEM_AC_USER_COUNT.format(problem=problem_id, contest=contest_id)
        if cache_name not in cache_res.keys():
            invalidate_problem(problem_id, contest_id)
            ans[problem_id] = cache.get(cache_name)
        else:
            ans[problem_id] = cache_res[cache_name]
    return ans


def invalidate_problem(problem_id, contest_id=0):
    cache_time = 300 * uniform(0.6, 1)
    if contest_id > 0:
        cache_time = 60 * uniform(0.6, 1)
        problem_filter = Submission.objects.filter(problem_id=problem_id, contest_id=contest_id).all()
    else:
        problem_filter = Submission.objects.filter(problem_id=problem_id).all()
    problem_accept_filter = problem_filter.filter(status=SubmissionStatus.ACCEPTED).all()

    all_count = problem_filter.count()
    accept_count = problem_accept_filter.count()
    accept_ratio = int(accept_count / all_count * 100)
    all_user_count = problem_filter.values('author_id').distinct().count()
    accept_user_count = problem_accept_filter.values("author_id").distinct().count()
    accept_user_ratio = int(accept_user_count / all_user_count * 100)

    cache.set(PROBLEM_ALL_COUNT.format(problem=problem_id, contest=contest_id), all_count, cache_time)
    cache.set(PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest_id), accept_count, cache_time)
    cache.set(PROBLEM_ALL_USER_COUNT.format(problem=problem_id, contest=contest_id), all_user_count, cache_time)
    cache.set(PROBLEM_AC_USER_COUNT.format(problem=problem_id, contest=contest_id), accept_user_count, cache_time)
    cache.set(PROBLEM_AC_RATIO.format(problem=problem_id, contest=contest_id), accept_ratio, cache_time)
    cache.set(PROBLEM_AC_USER_RATIO.format(problem=problem_id, contest=contest_id), accept_user_ratio, cache_time)