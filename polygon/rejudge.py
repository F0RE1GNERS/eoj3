from django.db import transaction
from django.core.cache import cache
from django_q.tasks import async

from contest.models import Contest
from problem.models import Problem
from contest.tasks import judge_submission_on_contest
from problem.tasks import judge_submission_on_problem
from submission.models import SubmissionStatus
from time import sleep
from threading import Thread


REJUDGE_TASK_LIMIT = 24
REJUDGE_COUNTER = 'rejudge_counter'


def rejudge_submission(submission, callback=None):
    if submission.contest_id:
        judge_submission_on_contest(submission, callback=callback, sync=True)
    else:
        judge_submission_on_problem(submission, callback=callback, sync=True)


def rejudge_submission_set(submission_set):
    with transaction.atomic():
        for submission in submission_set:
            submission.status = SubmissionStatus.WAITING
            submission.status_test = 0
            submission.status_percent = 0
            submission.status_detail = ""
            submission.status_message = ""
            submission.save(update_fields=["status", "status_detail", "status_message", "status_test", "status_percent"])

    for submission in submission_set:
        async(rejudge_submission, submission)


def rejudge_all_submission_on_contest(contest: Contest):
    Thread(target=rejudge_submission_set, args=(contest.submission_set.order_by("create_time"),)).start()


def rejudge_all_submission_on_contest_problem(contest: Contest, problem: Problem):
    Thread(target=rejudge_submission_set, args=(contest.submission_set.order_by("create_time").filter(problem=problem),)).start()


def rejudge_all_submission_on_problem(problem: Problem):
    Thread(target=rejudge_submission_set,
           args=(problem.submission_set.order_by("create_time").filter(contest__isnull=True),)) \
        .start()
