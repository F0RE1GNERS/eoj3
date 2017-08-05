import json
from random import uniform
from threading import Thread

from django.core.cache import cache

from dispatcher.models import Server
from dispatcher.manage import upload_case, upload_checker, upload_interactor, upload_validator
from dispatcher.judge import send_judge_through_watch
from submission.models import Submission, SubmissionStatus
from .models import Problem, SpecialProgram
from utils.detail_formatter import response_fail_with_timestamp

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
           (not problem.checker or upload_checker(server, SpecialProgram.objects.get(fingerprint=problem.checker))) and \
           (not problem.validator or upload_validator(server, SpecialProgram.objects.get(fingerprint=problem.validator))) and \
           (not problem.interactor or upload_interactor(server, SpecialProgram.objects.get(fingerprint=problem.interactor)))


def create_submission(problem, author, code, lang, contest=None):
    assert len(code) > 0 and len(code) <= 65536
    return Submission.objects.create(lang=lang, code=code, author=author, problem=problem, contest=contest)


def judge_submission_on_problem(submission, callback=None, **kwargs):
    """
    :type submission: Submission
    :param callback: function, call when judge result is received
    :return:
    """

    problem = submission.problem
    case_list = problem.case_list

    def on_receive_data(data):
        if data.get('status') == 'received':
            # TODO: cache
            if 'message' in data:
                submission.status_message = data['message']
            submission.status = data.get('verdict', SubmissionStatus.WAITING)
            submission.status_detail_list = data.get('detail', [])
            submission.status_detail_list = submission.status_detail_list + \
                                            [{}] * max(0, len(case_list) - len(submission.status_detail_list))
            submission.save(update_fields=['status_message', 'status_detail', 'status'])
            if SubmissionStatus.is_judged(data.get('verdict')):
                submission.status_time = max(map(lambda d: d.get('time', 0.0), submission.status_detail_list))
                submission.save(update_fields=['status_time'])
                Thread(callback).start()
                return True
            return False
        else:
            submission.status = SubmissionStatus.SYSTEM_ERROR
            submission.status_message = data['message']
            submission.save(update_fields=['status', 'status_message'])
            return True


    try:
        server = Server.objects.get(enabled=True)
        Thread(target=send_judge_through_watch, args=(server, submission.code, submission.lang, problem.time_limit,
                                                      problem.memory_limit, kwargs.get('run_until_complete', False),
                                                      problem.case_list, problem.checker, problem.interactor,
                                                      on_receive_data))\
            .start()
    except:
        on_receive_data(response_fail_with_timestamp())
