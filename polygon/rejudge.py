from django.db import transaction
from django.core.cache import cache
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
        judge_submission_on_contest(submission, callback)
    else:
        judge_submission_on_problem(submission, callback)


def rejudge_submission_set(submission_set):
    cache.set(REJUDGE_COUNTER, 0)

    def decrease_counter():
        try:
            cache.decr(REJUDGE_COUNTER, 1)
        except ValueError:
            cache.set(REJUDGE_COUNTER, 0)

    with transaction.atomic():
        for submission in submission_set:
            submission.status_private = submission.status = SubmissionStatus.WAITING
            submission.save(update_fields=["status_private", "status"])

    for submission in submission_set:
        while cache.get_or_set(REJUDGE_COUNTER, 0) >= REJUDGE_TASK_LIMIT:
            sleep(1)
        try:
            cache.incr(REJUDGE_COUNTER, 1)
        except:
            cache.set(REJUDGE_COUNTER, 0)
        rejudge_submission(submission, decrease_counter)


def rejudge_all_submission_on_contest(contest: Contest):
    Thread(target=rejudge_submission_set, args=(contest.submission_set.order_by("create_time"),)).start()


def rejudge_all_submission_on_problem(problem: Problem):
    Thread(target=rejudge_submission_set,
           args=(problem.submission_set.order_by("create_time").filter(contest__isnull=True),)) \
        .start()
