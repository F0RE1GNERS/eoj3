import re
from collections import Counter
from datetime import datetime
from os import path

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from account.models import User
from account.payment import reward_problem_ac, reward_contest_ac
from dispatcher.judge import send_judge_through_watch
from dispatcher.manage import upload_case, upload_checker, upload_interactor, upload_validator
from dispatcher.models import Server
from problem.statistics import invalidate_user
from submission.models import Submission, SubmissionReport
from submission.util import SubmissionStatus
from utils.detail_formatter import response_fail_with_timestamp
from .models import Problem, SpecialProgram, ProblemRewardStatus
from .statistics import invalidate_problem


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
        raise ValueError(_("Code length too short or too long."))
    if lang == "java":
        matching_regex = r"public\s+(final\s+)?class\s+Main"
        if re.search(matching_regex, code) is None:
            raise ValueError(_("Java Code should match regex: ") + matching_regex)
    if author.submission_set.exists() and (
        datetime.now() - author.submission_set.first().create_time).total_seconds() < settings.SUBMISSION_INTERVAL_LIMIT:
        raise ValueError(_("Please don't resubmit in 5 seconds."))
    if contest:
        if contest.submission_set.filter(author=author, problem_id=problem, code=code, lang=lang).exists():
            raise ValueError(_("You have submitted this code before."))
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
                        if submission.contest_time is not None:
                            reward_contest_ac(submission.author, 4 * problem.level ** 2, submission.contest_id)
                        else:
                            reward_problem_ac(submission.author, problem.reward, submission.problem_id)

                invalidate_user(submission.author_id, submission.contest_id)
                invalidate_problem(submission.problem)
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
        report_instance, _ = SubmissionReport.objects.get_or_create(submission=submission)
        report_instance.content = ""
        report_instance.save()
        send_judge_through_watch(code, submission.lang,
                                 problem.judging_time_limit or problem.time_limit,
                                 problem.judging_memory_limit or problem.memory_limit,
                                 kwargs.get('run_until_complete', False),
                                 case_list, problem.checker, problem.interactor, group_config,
                                 on_receive_data, report_instance=report_instance)
    except:
        on_receive_data(response_fail_with_timestamp())
