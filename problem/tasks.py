from datetime import datetime
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


def create_submission(problem, author, code, lang, contest=None, status=SubmissionStatus.WAITING):
    assert len(code) > 0 and len(code) <= 65536
    if isinstance(problem, (int, str)):
        return Submission.objects.create(lang=lang, code=code, author=author, problem_id=problem, contest=contest,
                                         status=status, status_private=status)
    else:
        return Submission.objects.create(lang=lang, code=code, author=author, problem=problem, contest=contest,
                                         status=status, status_private=status)


def judge_submission_on_problem(submission, callback=None, **kwargs):
    """
    :type submission: Submission
    :param callback: function, call when judge result is received
    :param status_private: make the status private only (when the contest scoreboard is frozen)
    :param case: can be pretest or sample or all
    :return:
    """

    problem = submission.problem
    case_list = []
    if kwargs.get('case') == 'pretest':
        case_list = problem.pretest_list
    elif kwargs.get('case') == 'sample':
        case_list = problem.sample_list
    if not case_list:  # case list is empty (e.g. something wrong with pretest list)
        case_list = problem.case_list
    point_query = dict(zip(problem.case_list, problem.point_list))

    def on_receive_data(data):
        judge_time = datetime.fromtimestamp(data['timestamp'])
        if submission.judge_end_time and judge_time < submission.judge_end_time:
            return True
        if data.get('status') == 'received':
            if 'message' in data:
                submission.status_message = data['message']
            submission.status_private = data.get('verdict', SubmissionStatus.JUDGING)
            if not kwargs.get('status_private'):
                submission.status = data.get('verdict', SubmissionStatus.JUDGING)
            else:
                submission.status = SubmissionStatus.SUBMITTED

            details = data.get('detail', [])
            # Add points to details
            for index, detail in enumerate(details):
                detail['score'] = point_query.get(case_list[index], 10)  # 10 points by default
            for index in range(len(details), len(case_list)):
                details.append({'score': point_query.get(case_list[index], 10)})
            submission.status_detail_list = details
            submission.save(update_fields=['status_message', 'status_detail', 'status', 'status_private'])

            if SubmissionStatus.is_judged(data.get('verdict')):
                submission.status_time = max(map(lambda d: d.get('time', 0.0), submission.status_detail_list))
                submission.judge_end_time = judge_time
                submission.save(update_fields=['status_time', 'judge_end_time'])
                if callback:
                    Thread(target=callback).start()
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
