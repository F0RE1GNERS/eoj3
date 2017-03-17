from django.db import transaction

from .models import Contest
from account.models import User
from submission.models import SubmissionStatus


def recalculate_score_for_participant(participant, submissions):
    """
    :param participant:
    :param submissions:
    :return: calculated score
    """
    # TODO: fix bugs
    INF = 2000000000
    score = 0
    for submission in submissions:
        if submission.status == SubmissionStatus.ACCEPTED:
            score += INF - 1200
        else:
            score -= 1200
    return score


def update_contest(contest_id, problem_id, user_id, accept_increment):
    """
    The three things we are going to do:
    1. update AC / Submit for ContestProblem
    2. update User (Participant) score
    3. update standings
    :param contest_id: the contest that is going to be affected
    :param problem_id: the problem that is going to be affected
    :param user_id: the user that is going to be affected
    :param accept_increment: does the submission increase AC or decrease?
    """
    with transaction.atomic():
        contest = Contest.objects.get(pk=contest_id)
        problem = contest.contestproblem_set.select_for_update().get(problem__pk=problem_id)
        problem.add_accept(accept_increment)
        problem.save()

        submissions = contest.submission_set.filter(author__pk=user_id)
        participant, _ = contest.contestparticipants_set.select_for_update().get_or_create(user__pk=user_id,
                            defaults={'user': User.objects.get(pk=user_id), 'contest': contest})
        participant.score = recalculate_score_for_participant(participant, submissions)
        participant.save()
