from random import uniform
from math import log10

from django.core.cache import cache

from problem.models import Problem
from submission.models import SubmissionStatus, Submission

PROBLEM_AC_USER_COUNT = 'p{problem}_c{contest}_ac_user_count'
PROBLEM_ALL_USER_COUNT = 'p{problem}_c{contest}_all_user_count'
PROBLEM_AC_USER_RATIO = 'p{problem}_c{contest}_ac_ratio_user'
PROBLEM_AC_COUNT = 'p{problem}_c{contest}_ac_count'
PROBLEM_ALL_COUNT = 'p{problem}_c{contest}_all_count'
PROBLEM_AC_RATIO = 'p{problem}_c{contest}_ac_ratio'
PROBLEM_DIFFICULTY = 'p{problem}_c{contest}_difficulty'
PROBLEM_ALL_DIFFICULTY = 'pa_difficulty'
PROBLEM_ALL_ACCEPT_COUNT = 'pa_ac_count'
PROBLEM_STATS = 'p{problem}_c{contest}_stats'


def _get_or_invalidate(problem_id, contest_id, cache_name):
    t = cache.get(cache_name)
    if t is None:
        invalidate_problems([problem_id], contest_id)
        return cache.get(cache_name)
    else:
        return t


def _get_many_or_invalidate(problem_ids, contest_id, cache_template):
    cache_res = cache.get_many(list(map(lambda x: cache_template.format(problem=x, contest=contest_id),
                                        problem_ids)))
    ans = dict()
    second_attempt = []
    for problem_id in problem_ids:
        cache_name = cache_template.format(problem=problem_id, contest=contest_id)
        if cache_name not in cache_res:
            second_attempt.append(problem_id)
        else:
            ans[problem_id] = cache_res[cache_name]
    invalidate_problems(second_attempt, contest_id)
    if second_attempt:
        res2 = cache.get_many(list(map(lambda x: cache_template.format(problem=x, contest=contest_id),
                                       second_attempt)))
        for problem_id in problem_ids:
            cache_name = cache_template.format(problem=problem_id, contest=contest_id)
            if cache_name in res2:
                ans[problem_id] = res2[cache_name]
    assert len(ans) == len(problem_ids)
    return ans


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


def get_problem_difficulty(problem_id):
    cache_name = PROBLEM_DIFFICULTY.format(problem=problem_id, contest=0)
    return _get_or_invalidate(problem_id, 0, cache_name)


def get_many_problem_accept_count(problem_ids, contest_id=0):
    return _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_AC_USER_COUNT)


def get_many_problem_difficulty(problem_ids):
    return _get_many_or_invalidate(problem_ids, 0, PROBLEM_DIFFICULTY)


def get_all_problem_difficulty():
    cache_time = 180
    return cache.get_or_set(PROBLEM_ALL_DIFFICULTY,
                            get_many_problem_difficulty(problem_ids=Problem.objects.all().values_list('id', flat=True)),
                            cache_time)


def get_all_accept_count():
    cache_time = 180
    return cache.get_or_set(PROBLEM_ALL_ACCEPT_COUNT,
                            get_many_problem_accept_count(problem_ids=Problem.objects.all().values_list('id', flat=True)),
                            cache_time)


def get_problem_stats(problem_id):
    cache_name = PROBLEM_STATS.format(problem=problem_id, contest=0)
    return _get_or_invalidate(problem_id, 0, cache_name)


def invalidate_problems(problem_ids, contest_id=0):
    if contest_id > 0:
        cache_time = 60 * uniform(0.6, 1)
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids, contest_id=contest_id).\
            only('problem_id', 'contest_id', 'author_id', 'status')
    else:
        cache_time = 300 * uniform(0.6, 1)
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids). \
            only('problem_id', 'author_id', 'status')

    all_count = {problem_id: 0 for problem_id in problem_ids}
    accept_count = {problem_id: 0 for problem_id in problem_ids}
    wa_count = {problem_id: 0 for problem_id in problem_ids}
    tle_count = {problem_id: 0 for problem_id in problem_ids}
    re_count = {problem_id: 0 for problem_id in problem_ids}
    ce_count = {problem_id: 0 for problem_id in problem_ids}
    all_user = {problem_id: set() for problem_id in problem_ids}
    accept_user = {problem_id: set() for problem_id in problem_ids}
    cache_res = {}

    for submission in problem_filter:
        pid = submission.problem_id
        status = submission.status
        if status == SubmissionStatus.ACCEPTED:
            accept_count[pid] += 1
            accept_user[pid].add(submission.author_id)
        elif status == SubmissionStatus.WRONG_ANSWER:
            wa_count[pid] += 1
        elif status == SubmissionStatus.TIME_LIMIT_EXCEEDED:
            tle_count[pid] += 1
        elif status == SubmissionStatus.RUNTIME_ERROR:
            re_count[pid] += 1
        elif status == SubmissionStatus.COMPILE_ERROR:
            ce_count[pid] += 1
        all_count[pid] += 1
        all_user[pid].add(submission.author_id)

    for problem_id in problem_ids:
        accept_user_count = len(accept_user[problem_id])
        all_user_count = len(all_user[problem_id])
        if all_user_count > 0:
            accept_ratio = accept_count[problem_id] / all_count[problem_id] * 100
            accept_user_ratio = accept_user_count / all_user_count * 100
        else:
            accept_ratio = accept_user_ratio = 0
        difficulty = max(min(5 - (.02 * accept_ratio + .03 * accept_user_ratio) * min(log10(accept_user_count + 1), 1.2)
                             + max(6 - 2 * log10(accept_user_count + 1), 0), 9.9), 0.1)
        cache_res.update({
            PROBLEM_ALL_COUNT.format(problem=problem_id, contest=contest_id): all_count[problem_id],
            PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest_id): accept_count[problem_id],
            PROBLEM_ALL_USER_COUNT.format(problem=problem_id, contest=contest_id): all_user_count,
            PROBLEM_AC_USER_COUNT.format(problem=problem_id, contest=contest_id): accept_user_count,
            PROBLEM_AC_RATIO.format(problem=problem_id, contest=contest_id): accept_ratio,
            PROBLEM_AC_USER_RATIO.format(problem=problem_id, contest=contest_id): accept_user_ratio,
            PROBLEM_DIFFICULTY.format(problem=problem_id, contest=contest_id): difficulty,
            PROBLEM_STATS.format(problem=problem_id, contest=contest_id): {
                'ac': accept_count[problem_id],
                'wa': wa_count[problem_id],
                'tle': tle_count[problem_id],
                're': re_count[problem_id],
                'ce': ce_count[problem_id],
                'others': all_count[problem_id] - accept_count[problem_id] - wa_count[problem_id]
                          - tle_count[problem_id] - re_count[problem_id] - ce_count[problem_id],
            }
        })

    cache.set_many(cache_res, cache_time)


def get_contest_problem_ac_submit(problem_ids, contest_id):
    ac_count = _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_AC_COUNT)
    submit_count = _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_ALL_COUNT)
    ans = dict()
    for problem in problem_ids:
        ans[problem] = dict(ac=ac_count.get(problem, 0), submit=submit_count.get(problem, 0))
    return ans
