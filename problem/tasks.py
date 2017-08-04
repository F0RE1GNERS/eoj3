from random import uniform

from django.core.cache import cache

from dispatcher.models import Server
from dispatcher.manage import upload_case, upload_checker, upload_interactor, upload_validator
from submission.models import Submission, SubmissionStatus
from .models import Problem, SpecialProgram

PROBLEM_AC_COUNT_FOR_CONTEST = 'problem_{problem}_ac_in_contest_{contest}'


def get_problem_accept_count(problem_id, contest_id=0):
    """
    get problem count, with cache

    :type problem_id: int
    :param contest_id: do not use it or set it to 0 if no contest is specified
    :return:
    """
    return get_many_problem_accept_count([problem_id], contest_id)[problem_id]


def get_many_problem_accept_count(problem_ids, contest_id=0):
    cache_res = cache.get_many(list(map(lambda x: PROBLEM_AC_COUNT_FOR_CONTEST.format(problem=x, contest=contest_id),
                                        problem_ids)))
    ans = dict()
    for problem_id in problem_ids:
        cache_name = PROBLEM_AC_COUNT_FOR_CONTEST.format(problem=problem_id, contest=contest_id)
        if cache_name not in cache_res.keys():
            filter_rule = dict(problem_id=problem_id, status=SubmissionStatus.ACCEPTED)
            if contest_id:
                filter_rule.update(contest_id=contest_id)
            count = Submission.objects.filter(**filter_rule).values('author_id').distinct().count()
            ans[problem_id] = count
            if contest_id:  # relatively low cache time for contests
                cache_time = 60 * uniform(0.6, 1)
            else:
                cache_time = 300 * uniform(0.6, 1)
            cache.set(cache_name, count, cache_time)
        else:
            ans[problem_id] = cache_res[cache_name]
    return ans


def upload_problem_to_judge_server(problem, server):
    """
    :param problem: the problem to be uploaded
    :type problem: Problem
    :type server: Server
    """
    return all(upload_case(server, case) for case in problem.case_list) and \
           (problem.checker and upload_checker(server, SpecialProgram.objects.get(fingerprint=problem.checker))) and \
           (problem.validator and upload_validator(server, SpecialProgram.objects.get(fingerprint=problem.validator))) and \
           (problem.interactor and upload_interactor(server, SpecialProgram.objects.get(fingerprint=problem.interactor)))
