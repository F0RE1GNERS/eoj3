from threading import Thread

from dispatcher.judge import send_judge_through_watch
from dispatcher.manage import upload_case, upload_checker, upload_interactor, upload_validator
from dispatcher.models import Server
from submission.models import Submission, SubmissionStatus
from utils.detail_formatter import response_fail_with_timestamp
from .models import Problem, SpecialProgram


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
