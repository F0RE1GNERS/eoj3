from random import uniform
from math import log10
from time import sleep

from django.core.cache import cache

from problem.models import Problem
from submission.models import SubmissionStatus, Submission
from utils.permission import is_problem_manager

PROBLEM_AC_USER_COUNT = 'p{problem}_c{contest}_ac_user_count'
PROBLEM_TOTAL_USER_COUNT = 'p{problem}_c{contest}_all_user_count'
PROBLEM_AC_USER_RATIO = 'p{problem}_c{contest}_ac_ratio_user'
PROBLEM_AC_COUNT = 'p{problem}_c{contest}_ac_count'
PROBLEM_TOTAL_SUB_COUNT = 'p{problem}_c{contest}_all_count'
PROBLEM_AC_RATIO = 'p{problem}_c{contest}_ac_ratio'
PROBLEM_DIFFICULTY = 'p{problem}_c{contest}_difficulty'
PROBLEM_MAX_SCORE = 'p{problem}_c{contest}_max_score'
PROBLEM_AVG_SCORE = 'p{problem}_c{contest}_avg_score'
PROBLEM_DIFFICULTY_FOR_REWARD = 'p{problem}_reward'
PROBLEM_ALL_DIFFICULTY = 'pa_difficulty'
PROBLEM_ALL_ACCEPT_COUNT = 'pa_ac_count'
PROBLEM_ALL_SUB_COUNT = 'pa_sub_count'
PROBLEM_STATS = 'p{problem}_c{contest}_stats'
FORTNIGHT = 14 * 86400


def _get_or_invalidate(problem_id, contest_id, cache_name):
    t = cache.get(cache_name)
    if t is None: return update_problems([problem_id], contest_id).get(cache_name)
    else: return t


def _get_many_or_invalidate(problem_ids, contest_id, cache_template):
    MAX_RETRY = 3
    for _retry in range(MAX_RETRY):
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
        update_problems(second_attempt, contest_id)
        if second_attempt:
            res2 = cache.get_many(list(map(lambda x: cache_template.format(problem=x, contest=contest_id),
                                           second_attempt)))
            for problem_id in problem_ids:
                cache_name = cache_template.format(problem=problem_id, contest=contest_id)
                if cache_name in res2:
                    ans[problem_id] = res2[cache_name]
        if len(ans) == len(problem_ids):
            return ans
        sleep(1)
    raise AssertionError("Problem cache invalidate out of attempts")


def get_problem_accept_user_count(problem_id, contest_id=0):
    """
    get problem accept count (user), with cache

    :type problem_id: int
    :return:
    """
    return get_many_problem_accept_count([problem_id], contest_id)[problem_id]


def get_problem_all_user_count(problem_id, contest_id=0):
    cache_name = PROBLEM_TOTAL_USER_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_user_ratio(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_USER_RATIO.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_count(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_all_count(problem_id, contest_id=0):
    cache_name = PROBLEM_TOTAL_SUB_COUNT.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_accept_ratio(problem_id, contest_id=0):
    cache_name = PROBLEM_AC_RATIO.format(problem=problem_id, contest=contest_id)
    return _get_or_invalidate(problem_id, contest_id, cache_name)


def get_problem_difficulty(problem_id):
    cache_name = PROBLEM_DIFFICULTY.format(problem=problem_id, contest=0)
    return _get_or_invalidate(problem_id, 0, cache_name)


def get_problem_reward(problem_id):
    def default():
        return get_problem_difficulty(problem_id)
    return cache.get_or_set(PROBLEM_DIFFICULTY_FOR_REWARD.format(problem=problem_id), default) or 5.0


def get_many_problem_accept_count(problem_ids, contest_id=0):
    return _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_AC_USER_COUNT)


def get_many_problem_tried_count(problem_ids, contest_id=0):
    return _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_TOTAL_USER_COUNT)


def get_many_problem_max_score(problem_ids, contest_id=0):
    return _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_MAX_SCORE)


def get_many_problem_avg_score(problem_ids, contest_id=0):
    return _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_AVG_SCORE)


def get_many_problem_difficulty(problem_ids):
    return _get_many_or_invalidate(problem_ids, 0, PROBLEM_DIFFICULTY)


def get_all_problem_difficulty():
    def default():
        return get_many_problem_difficulty(problem_ids=Problem.objects.all().values_list('id', flat=True))
    return cache.get_or_set(PROBLEM_ALL_DIFFICULTY, default)


def get_all_accept_count():
    def default():
        return get_many_problem_accept_count(problem_ids=Problem.objects.all().values_list('id', flat=True))
    return cache.get_or_set(PROBLEM_ALL_ACCEPT_COUNT, default)


def get_all_tried_user_count():
    def default():
        return get_many_problem_tried_count(problem_ids=Problem.objects.all().values_list('id', flat=True))
    return cache.get_or_set(PROBLEM_ALL_SUB_COUNT, default)


def get_problem_stats(problem_id):
    cache_name = PROBLEM_STATS.format(problem=problem_id, contest=0)
    return _get_or_invalidate(problem_id, 0, cache_name)


def invalidate_problem(problem_id, contest_id=0):
    if contest_id is None:
        contest_id = 0
    for contest in {contest_id, 0}:
        cache.delete_many([PROBLEM_TOTAL_SUB_COUNT.format(problem=problem_id, contest=contest),
                           PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest),
                           PROBLEM_TOTAL_USER_COUNT.format(problem=problem_id, contest=contest),
                           PROBLEM_AC_USER_COUNT.format(problem=problem_id, contest=contest),
                           PROBLEM_AC_RATIO.format(problem=problem_id, contest=contest),
                           PROBLEM_AC_USER_RATIO.format(problem=problem_id, contest=contest),
                           PROBLEM_DIFFICULTY.format(problem=problem_id, contest=contest),
                           PROBLEM_STATS.format(problem=problem_id, contest=contest)])


def update_problems(problem_ids, contest_id=0):
    if contest_id > 0:
        cache_time = FORTNIGHT * uniform(0.6, 1)
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids, contest_id=contest_id).\
            only('problem_id', 'contest_id', 'author_id', 'status', 'status_percent')
    else:
        cache_time = FORTNIGHT * uniform(0.6, 1)
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids). \
            only('problem_id', 'author_id', 'status', 'status_percent')

    all_count = {problem_id: 0 for problem_id in problem_ids}
    accept_count = {problem_id: 0 for problem_id in problem_ids}
    wa_count = {problem_id: 0 for problem_id in problem_ids}
    tle_count = {problem_id: 0 for problem_id in problem_ids}
    re_count = {problem_id: 0 for problem_id in problem_ids}
    ce_count = {problem_id: 0 for problem_id in problem_ids}
    max_score = {problem_id: 0 for problem_id in problem_ids}
    average_score = {problem_id: 0 for problem_id in problem_ids}
    all_user = {problem_id: set() for problem_id in problem_ids}
    accept_user = {problem_id: set() for problem_id in problem_ids}
    scores = {problem_id: dict() for problem_id in problem_ids}
    cache_res = {}

    for submission in problem_filter:
        pid = submission.problem_id
        status = submission.status
        if SubmissionStatus.is_accepted(status):
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
        scores[pid].setdefault(submission.author_id, 0.0)
        scores[pid][submission.author_id] = max(scores[pid][submission.author_id], submission.status_percent)

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
        if scores[problem_id]:
            s = list(scores[problem_id].values())
            max_score[problem_id] = max(s)
            average_score[problem_id] = sum(s) / len(s)
        else:
            max_score[problem_id] = 0.0
            average_score[problem_id] = 0.0
        cache_res.update({
            PROBLEM_TOTAL_SUB_COUNT.format(problem=problem_id, contest=contest_id): all_count[problem_id],
            PROBLEM_AC_COUNT.format(problem=problem_id, contest=contest_id): accept_count[problem_id],
            PROBLEM_TOTAL_USER_COUNT.format(problem=problem_id, contest=contest_id): all_user_count,
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
            },
            PROBLEM_MAX_SCORE.format(problem=problem_id, contest=contest_id): max_score[problem_id],
            PROBLEM_AVG_SCORE.format(problem=problem_id, contest=contest_id): average_score[problem_id],
        })

    cache.set_many(cache_res, cache_time)
    return cache_res


def get_contest_problem_ac_submit(problem_ids, contest_id):
    ac_count = _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_AC_COUNT)
    submit_count = _get_many_or_invalidate(problem_ids, contest_id, PROBLEM_TOTAL_SUB_COUNT)
    ans = dict()
    for problem in problem_ids:
        ans[problem] = dict(ac=ac_count.get(problem, 0), submit=submit_count.get(problem, 0))
    return ans


USER_TOTAL_COUNT = 'u{user}_c{contest}_total_count'
USER_TOTAL_LIST = 'u{user}_c{contest}_total_list'
USER_AC_COUNT = 'u{user}_c{contest}_ac_count'
USER_AC_DIFF_COUNT = 'u{user}_c{contest}_ac_diff'
USER_AC_LIST = 'u{user}_c{contest}_ac_list'
USER_UPDATE_TIME = 'u{user}_c{contest}_update_time'


def _get_or_invalidate_user(user_id, contest_id, cache_name):
    t = cache.get(cache_name)
    if t is None:
        update_user(user_id, contest_id)
        return cache.get(cache_name)
    else:
        return t


def get_accept_submission_count(user_id, contest_id=0):
    cache_name = USER_AC_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate_user(user_id, contest_id, cache_name)


def get_accept_problem_count(user_id, contest_id=0):
    cache_name = USER_AC_DIFF_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate_user(user_id, contest_id, cache_name)


def get_accept_problem_list(user_id, contest_id=0):
    cache_name = USER_AC_LIST.format(user=user_id, contest=contest_id)
    return _get_or_invalidate_user(user_id, contest_id, cache_name)


def get_total_submission_count(user_id, contest_id=0):
    cache_name = USER_TOTAL_COUNT.format(user=user_id, contest=contest_id)
    return _get_or_invalidate_user(user_id, contest_id, cache_name)


def get_attempted_problem_list(user_id, contest_id=0):
    cache_name = USER_TOTAL_LIST.format(user=user_id, contest=contest_id)
    return _get_or_invalidate_user(user_id, contest_id, cache_name)


def invalidate_user(user_id, contest_id=0):
    if contest_id is None:
        contest_id = 0
    for contest in {contest_id, 0}:
        cache.delete_many([USER_TOTAL_COUNT.format(user=user_id, contest=contest),
                           USER_TOTAL_LIST.format(user=user_id, contest=contest),
                           USER_AC_COUNT.format(user=user_id, contest=contest),
                           USER_AC_DIFF_COUNT.format(user=user_id, contest=contest),
                           USER_AC_LIST.format(user=user_id, contest=contest)])


def update_user(user_id, contest_id=0):
    cache_time = FORTNIGHT * uniform(0.8, 1)
    if contest_id > 0:
        cache_time = FORTNIGHT * uniform(0.8, 1)
        submission_filter = Submission.objects.filter(author_id=user_id, contest_id=contest_id).all()
    else:
        submission_filter = Submission.objects.filter(author_id=user_id).all()
    ac_filter = submission_filter.filter(status__in=[SubmissionStatus.ACCEPTED, SubmissionStatus.PRETEST_PASSED]).all()

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


def is_problem_accepted(user, problem):
    return is_problem_manager(user, problem) or (user.is_authenticated and
           user.submission_set.filter(problem=problem, status=SubmissionStatus.ACCEPTED).exists())