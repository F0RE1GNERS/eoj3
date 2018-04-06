import random
from datetime import datetime
from threading import Thread

from django import db
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from os import path

from account.models import User
from account.payment import reward_problem_ac, reward_contest_ac
from dispatcher.judge import send_judge_through_watch
from dispatcher.manage import upload_case, upload_checker, upload_interactor, upload_validator
from dispatcher.models import Server
from submission.models import Submission, SubmissionStatus
from submission.statistics import invalidate_user
from utils.detail_formatter import response_fail_with_timestamp
from utils.language import LANG_CHOICE
from .models import Problem, SpecialProgram, ProblemRewardStatus
from .statistics import get_problem_difficulty, invalidate_problem, get_problem_reward


def upload_problem_to_judge_server(problem, server):
    """
    :param problem: the problem to be uploaded
    :type problem: Problem
    :type server: Server
    """
    return all(upload_case(server, case) for case in problem.case_list) and \
           (not problem.checker or upload_checker(server, SpecialProgram.objects.get(fingerprint=problem.checker))) and \
           (not problem.validator or upload_validator(server,
                                                      SpecialProgram.objects.get(fingerprint=problem.validator))) and \
           (not problem.interactor or upload_interactor(server,
                                                        SpecialProgram.objects.get(fingerprint=problem.interactor)))


def create_submission(problem, author: User, code, lang, contest=None, status=SubmissionStatus.WAITING, ip=''):
    if not 6 <= len(code) <= 65536:
        raise ValueError("Code is too short or too long.")
    if author.submission_set.exists() and (
        datetime.now() - author.submission_set.first().create_time).total_seconds() < 5:
        raise ValueError("Please don't resubmit in 5 seconds.")
    if isinstance(problem, (int, str)):
        return Submission.objects.create(lang=lang, code=code, author=author, problem_id=problem, contest=contest,
                                         status=status, status_private=status, ip=ip)
    else:
        return Submission.objects.create(lang=lang, code=code, author=author, problem=problem, contest=contest,
                                         status=status, status_private=status, ip=ip)


def process_failed_test(details):
    try:
        for idx, det in enumerate(details, start=1):
            if det.get('verdict') != 0:
                return idx
        return 0
    except (TypeError, ValueError, AttributeError):
        return 0


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
    total_score = max(1, sum(map(lambda x: point_query.get(x, 10), case_list)))
    status_for_pretest = kwargs.get('status_for_pretest', False)

    def process_accepted(status):
        if status == SubmissionStatus.ACCEPTED and status_for_pretest:
            return SubmissionStatus.PRETEST_PASSED
        else:
            return status

    def on_receive_data(data):
        judge_time = datetime.fromtimestamp(data['timestamp'])
        if submission.judge_end_time and judge_time < submission.judge_end_time:
            return True
        if data.get('status') == 'received':
            if 'message' in data:
                submission.status_message = data['message']
            else:
                submission.status_message = ''
            submission.status_private = process_accepted(data.get('verdict', SubmissionStatus.JUDGING))
            if not kwargs.get('status_private'):
                submission.status = process_accepted(data.get('verdict', SubmissionStatus.JUDGING))
            else:
                submission.status = SubmissionStatus.SUBMITTED

            details = data.get('detail', [])
            # Add points to details
            score = 0
            for index, detail in enumerate(details):
                if detail.get('verdict') == 0:
                    score += point_query.get(case_list[index], 10)
            submission.status_percent = score / total_score * 100
            submission.status_test = process_failed_test(details)
            submission.status_detail_list = details
            submission.status_detail_list += [{}] * max(0, len(case_list) - len(submission.status_detail_list))
            submission.save(
                update_fields=['status_message', 'status_detail', 'status', 'status_private', 'status_percent',
                               'status_test'])

            if SubmissionStatus.is_judged(data.get('verdict')):
                try:
                    submission.status_time = max(map(lambda d: d.get('time', 0.0), submission.status_detail_list))
                except ValueError: pass
                submission.judge_end_time = judge_time

                try: submission.judge_server = server.id
                except: pass

                submission.save(update_fields=['status_time', 'judge_end_time', 'judge_server'])
                difficulty = get_problem_reward(submission.problem_id)

                if submission.status == SubmissionStatus.ACCEPTED:
                    # Add reward
                    try:
                        ProblemRewardStatus.objects.create(problem_id=submission.problem_id,
                                                           user_id=submission.author_id)
                        if submission.contest_id:
                            reward_contest_ac(submission.author, difficulty, submission.contest_id)
                        else:
                            reward_problem_ac(submission.author, difficulty, submission.problem_id)
                    except db.IntegrityError:
                        pass

                invalidate_user(submission.author_id, submission.contest_id)
                invalidate_problem(submission.problem_id, submission.contest_id)
                if callback:
                    Thread(target=callback).start()
                return True
            return False
        else:
            submission.status = submission.status_private = SubmissionStatus.SYSTEM_ERROR
            submission.status_message = data['message']
            submission.save(update_fields=['status', 'status_message', 'status_private'])
            return True

    try:
        servers = Server.objects.filter(enabled=True)
        server = random.choice(servers)
        Thread(target=send_judge_through_watch, args=(server, submission.code, submission.lang, problem.time_limit,
                                                      problem.memory_limit, kwargs.get('run_until_complete', False),
                                                      problem.case_list, problem.checker, problem.interactor,
                                                      on_receive_data),
               kwargs={'report_file_path': path.join(settings.GENERATE_DIR,
                                                     'submission-%d' % submission.pk)}) \
            .start()
    except:
        on_receive_data(response_fail_with_timestamp())
