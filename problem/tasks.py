import random
from collections import Counter
from datetime import datetime, timedelta
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
from problem.statistics import invalidate_user
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
    for case in set(problem.pretest_list + problem.sample_list + problem.case_list):
        upload_case(server, case)
    if problem.checker:
        upload_checker(server, SpecialProgram.objects.get(fingerprint=problem.checker))
    if problem.validator:
        upload_validator(server, SpecialProgram.objects.get(fingerprint=problem.validator))
    if problem.interactor:
        upload_interactor(server, SpecialProgram.objects.get(fingerprint=problem.interactor))


def create_submission(problem, author: User, code, lang, contest=None, status=SubmissionStatus.WAITING, ip=''):
    if not 6 <= len(code) <= 65536:
        raise ValueError("Code is too short or too long.")
    if author.submission_set.exists() and (
        datetime.now() - author.submission_set.first().create_time).total_seconds() < settings.SUBMISSION_INTERVAL_LIMIT:
        raise ValueError("Please don't resubmit in 5 seconds.")
    if contest:
        if contest.submission_set.filter(author=author, problem_id=problem, code=code, lang=lang).exists():
            raise ValueError("You have submitted exactly the same code before.")
    if isinstance(problem, (int, str)):
        return Submission.objects.create(lang=lang, code=code, author=author, problem_id=problem, contest=contest,
                                         status=status, ip=ip)
    else:
        return Submission.objects.create(lang=lang, code=code, author=author, problem=problem, contest=contest,
                                         status=status, ip=ip)


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
    :param case: can be pretest or sample or all
    :return:
    """

    problem = submission.problem
    code = submission.code

    # concat code for template judging
    templates = problem.template_dict
    if submission.lang in templates:
        grader_code = templates[submission.lang]["grader"]
        insert_indicator = "$$template$$"
        if insert_indicator in grader_code:
            code = grader_code.replace(insert_indicator, code)
        else:
            code = code + '\n\n' + grader_code

    case_list = []
    group_config = {"on": False}
    if kwargs.get('case') == 'pretest':
        case_list = problem.pretest_list
    elif kwargs.get('case') == 'sample':
        case_list = problem.sample_list
    if not case_list:  # case list is empty (e.g. something wrong with pretest list)
        case_list = problem.case_list
        if problem.group_enabled:
            # enable group testing only when using whole testset mode
            group_config["on"] = True
            group_config["group_list"] = problem.group_list
            group_config["group_count"] = max(group_config["group_list"])
            group_config["group_dependencies"] = problem.group_dependencies

    if group_config["on"]:
        point_query = list(problem.point_list)
        total_score = max(1, sum(point_query))
    else:
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
            submission.status = process_accepted(data.get('verdict', SubmissionStatus.JUDGING))

            details = data.get('detail', [])
            if not group_config["on"]:
                # Add points to details
                score = 0
                try:
                    for index, detail in enumerate(details):
                        if 'point' not in detail:
                            if detail.get('verdict') == 0:
                                detail['point'] = point_query.get(case_list[index], 10) / total_score * 100
                        score += detail.get('point', 0)
                except:
                    pass
                submission.status_percent = score
            display_details = details + [{}] * max(0, len(case_list) - len(details))
            submission.status_detail_list = display_details
            submission.status_test = process_failed_test(display_details)
            submission.judge_server = data.get('server', 0)
            submission.save(update_fields=['status_message', 'status_detail','status',
                                           'status_percent', 'status_test', 'judge_server'])

            if SubmissionStatus.is_judged(data.get('verdict')):
                if group_config["on"] and data.get('verdict') != SubmissionStatus.COMPILE_ERROR:
                    score = 0
                    records = []
                    accept_case_counter, total_case_counter = Counter(), Counter()
                    for index, detail in enumerate(details):
                        group_id = group_config["group_list"][index]
                        if detail.get('verdict') == 0:
                            accept_case_counter[group_id] += 1
                        total_case_counter[group_id] += 1
                    for group_id in range(1, group_config["group_count"] + 1):
                        get_score = 0
                        if accept_case_counter[group_id] == total_case_counter[group_id] and \
                                total_case_counter[group_id] > 0:
                            get_score = point_query[group_id - 1]
                        score += get_score
                        records.append("Subtask #%d: " % group_id +
                                       "%d/%d cases passed. %d points." % (accept_case_counter[group_id],
                                                                           total_case_counter[group_id],
                                                                           get_score))
                    records.append("Total: %d/%d" % (score, total_score))
                    submission.status_message = "\n".join(records)
                    submission.status_percent = score / total_score * 100

                try:
                    submission.status_time = max(map(lambda d: d.get('time', 0.0), submission.status_detail_list))
                except ValueError: pass
                submission.judge_end_time = judge_time

                submission.save(update_fields=['status_time', 'judge_end_time', 'status_message', 'status_percent'])

                if submission.status == SubmissionStatus.ACCEPTED:
                    # Add reward
                    _, created = ProblemRewardStatus.objects.get_or_create(problem_id=submission.problem_id,
                                                                           user_id=submission.author_id)
                    if created:
                        if submission.contest_id and not submission.contest.always_running:
                            reward_contest_ac(submission.author, 50, submission.contest_id)
                        else:
                            difficulty = get_problem_reward(submission.problem_id)
                            reward_problem_ac(submission.author, difficulty, submission.problem_id)

                invalidate_user(submission.author_id, submission.contest_id)
                invalidate_problem(submission.problem_id, submission.contest_id)
                if callback:
                    callback()
                return True
            return False
        else:
            submission.status = SubmissionStatus.SYSTEM_ERROR
            submission.status_message = data['message']
            submission.save(update_fields=['status', 'status_message'])
            return True

    try:
        n_args = (code, submission.lang, problem.time_limit,
                  problem.memory_limit, kwargs.get('run_until_complete', False),
                  case_list, problem.checker, problem.interactor, group_config,
                  on_receive_data)
        n_kwargs = {'report_file_path': path.join(settings.GENERATE_DIR,
                                                  'submission-%d' % submission.pk)}

        send_judge_through_watch(*n_args, **n_kwargs)
    except:
        on_receive_data(response_fail_with_timestamp())
