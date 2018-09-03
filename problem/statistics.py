from random import uniform
from math import log10
from time import sleep

from django.core.cache import cache
from django.db import transaction

from problem.models import Problem, ProblemContestStatus, UserStatus, TagInfo
from submission.models import SubmissionStatus, Submission
from utils.permission import is_problem_manager


def recalculate_problems(problem_ids, contest_id=0):
    """

    :param problem_ids:
    :param contest_id: set to 0 if want to be null
    :return: {
        <problem_id>: {
            ac_user_count: <int>,
            total_user_count: <int>,
            ac_count: <int>,
            total_count: <int>,
            difficulty: <float>,
            max_score: <float>,
            avg_score: <float>,
            stats: <dict>
        },
        ...
    }
    """
    if contest_id:
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids, contest_id=contest_id). \
            defer("code", "status_message", "status_detail")
    else:
        problem_filter = Submission.objects.filter(problem_id__in=problem_ids). \
            defer("code", "status_message", "status_detail")

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
    ans = {}

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
        ans[problem_id] = {
            "ac_user_count": accept_user_count,
            "total_user_count": all_user_count,
            "ac_count": accept_count[problem_id],
            "total_count": all_count[problem_id],
            "difficulty": difficulty,
            "max_score": max_score[problem_id],
            "avg_score": average_score[problem_id],
            "stats": {
                'ac': accept_count[problem_id],
                'wa': wa_count[problem_id],
                'tle': tle_count[problem_id],
                're': re_count[problem_id],
                'ce': ce_count[problem_id],
                'others': all_count[problem_id] - accept_count[problem_id] - wa_count[problem_id]
                          - tle_count[problem_id] - re_count[problem_id] - ce_count[problem_id],
            },
        }

    return ans


def _select_problem_contest_status(problem_ids: list, contest_id):
    """
    get the objects, possibly empty, NO UPDATE

    :param problem_ids: a list of problem ids
    :param contest_id:
    :return: a list of ProblemContestStatus objects. empty pk for those who does not exist
    """
    s = {p.problem_id: p for p in ProblemContestStatus.objects.filter(problem_id__in=problem_ids, contest_id=contest_id)}
    res = []
    for problem_id in problem_ids:
        if problem_id in s:
            res.append(s[problem_id])
        else:
            res.append(ProblemContestStatus(problem_id=problem_id, contest_id=contest_id))
    return res


def invalidate_problem(problems, contest_id=0):
    """
    UPDATE everything

    :param problems: can be int, or list
    :param contest_id:
    :return: a list of ProblemContestStatus objects
    """
    if contest_id is None:
        contest_id = 0
    if contest_id != 0:
        invalidate_problem(problems)

    if isinstance(problems, int):
        problems = [problems]
    elif isinstance(problems, list):
        problems = problems
    else:
        raise ValueError

    res = recalculate_problems(problems, contest_id)
    pc = _select_problem_contest_status(problems, contest_id)
    with transaction.atomic():
        for p in pc:
            for attr, value in res[p.problem_id].items():
                setattr(p, attr, value)
            p.save()
    return pc


def _get_many_or_invalidate_problem(problem_ids, contest_id, field_name):
    pc = _select_problem_contest_status(problem_ids, contest_id)
    not_found = list(map(lambda x: x.problem_id, filter(lambda item: not item.pk, pc)))
    if not_found:
        invalidate_problem(not_found, contest_id)
        pc = _select_problem_contest_status(problem_ids, contest_id)
    return {p.problem_id: getattr(p, field_name) for p in pc}


def _get_or_invalidate_problem(problem_id, contest_id, field_name):
    return _get_many_or_invalidate_problem([problem_id], contest_id, field_name)[problem_id]


def get_problem_accept_user_count(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "ac_user_count")


def get_problem_all_user_count(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "total_user_count")


def get_problem_accept_user_ratio(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "ac_user_ratio")


def get_problem_accept_count(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "ac_count")


def get_problem_all_count(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "total_count")


def get_problem_accept_ratio(problem_id, contest_id=0):
    return _get_or_invalidate_problem(problem_id, contest_id, "ac_ratio")


def get_problem_difficulty(problem_id):
    return _get_or_invalidate_problem(problem_id, 0, "difficulty")


def get_problem_reward(problem_id):
    return get_problem_difficulty(problem_id) or 5.0


def get_many_problem_accept_count(problem_ids, contest_id=0):
    return _get_many_or_invalidate_problem(problem_ids, contest_id, "ac_user_count")


def get_many_problem_tried_count(problem_ids, contest_id=0):
    return _get_many_or_invalidate_problem(problem_ids, contest_id, "total_user_count")


def get_many_problem_max_score(problem_ids, contest_id=0):
    return _get_many_or_invalidate_problem(problem_ids, contest_id, "max_score")


def get_many_problem_avg_score(problem_ids, contest_id=0):
    return _get_many_or_invalidate_problem(problem_ids, contest_id, "avg_score")


def get_many_problem_difficulty(problem_ids):
    return _get_many_or_invalidate_problem(problem_ids, 0, "difficulty")


def get_all_problem_difficulty():
    return get_many_problem_difficulty(problem_ids=Problem.objects.all().values_list('id', flat=True))


def get_all_accept_count():
    return get_many_problem_accept_count(problem_ids=Problem.objects.all().values_list('id', flat=True))


def get_all_tried_user_count():
    return get_many_problem_tried_count(problem_ids=Problem.objects.all().values_list('id', flat=True))


def get_problem_stats(problem_id):
    return _get_or_invalidate_problem(problem_id, 0, "stats")


def get_contest_problem_ac_submit(problem_ids, contest_id):
    ac_count = _get_many_or_invalidate_problem(problem_ids, contest_id, "ac_count")
    submit_count = _get_many_or_invalidate_problem(problem_ids, contest_id, "total_count")
    ans = dict()
    for problem in problem_ids:
        ans[problem] = dict(ac=ac_count.get(problem, 0), submit=submit_count.get(problem, 0))
    return ans


def invalidate_user(user_id, contest_id=0):
    if contest_id is None:
        contest_id = 0
    if contest_id:
        invalidate_user(user_id)

    if contest_id:
        submission_filter = Submission.objects.filter(author_id=user_id, contest_id=contest_id).all()
    else:
        submission_filter = Submission.objects.filter(author_id=user_id).all()
    ac_filter = submission_filter.filter(status__in=[SubmissionStatus.ACCEPTED, SubmissionStatus.PRETEST_PASSED]).all()

    total_count = submission_filter.count()
    total_list = list(submission_filter.order_by().values_list("problem_id", flat=True).distinct())
    accept_count = ac_filter.count()
    accept_list = list(ac_filter.order_by().values_list("problem_id", flat=True).distinct())
    accept_diff = len(accept_list)

    us, _ = UserStatus.objects.get_or_create(user_id=user_id, contest_id=contest_id,
                                             defaults={
                                                 "total_count": total_count,
                                                 "total_list": ",".join(map(str, total_list)),
                                                 "ac_count": accept_count,
                                                 "ac_list": ",".join(map(str, accept_list)),
                                                 "ac_distinct_count": accept_diff
                                             })
    return us


def _get_or_invalidate_user(user_id, contest_id, field_name):
    try:
        return getattr(UserStatus.objects.get(user_id=user_id, contest_id=contest_id), field_name)
    except:
        return getattr(invalidate_user(user_id, contest_id), field_name)


def get_accept_submission_count(user_id, contest_id=0):
    return _get_or_invalidate_user(user_id, contest_id, "ac_count")


def get_accept_problem_count(user_id, contest_id=0):
    return _get_or_invalidate_user(user_id, contest_id, "ac_distinct_count")


def get_accept_problem_list(user_id, contest_id=0):
    t = _get_or_invalidate_user(user_id, contest_id, "ac_list")
    if not t: return []
    return list(map(int, t.split(',')))


def get_total_submission_count(user_id, contest_id=0):
    return _get_or_invalidate_user(user_id, contest_id, "total_count")


def get_attempted_problem_list(user_id, contest_id=0):
    t = _get_or_invalidate_user(user_id, contest_id, "total_list")
    if not t: return []
    return list(map(int, t.split(',')))


def is_problem_accepted(user, problem):
    return is_problem_manager(user, problem) or (user.is_authenticated and
           user.submission_set.filter(problem=problem, status=SubmissionStatus.ACCEPTED).exists())


def get_children_tag_id(tag: int = -1):
    tags = {tag}
    while True:
        adds = set(TagInfo.objects.filter(parent_id__in=tags).values_list("tag_id", flat=True))
        if (adds & tags) == adds:
            break
        tags |= adds
    return tags
