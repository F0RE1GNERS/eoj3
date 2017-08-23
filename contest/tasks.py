from django.utils import timezone
from django.db import transaction
from .models import Contest, ContestParticipant
from account.models import User
from problem.tasks import judge_submission_on_problem
from submission.models import SubmissionStatus, Submission
from functools import cmp_to_key
import time
from threading import Thread


def judge_submission_on_contest(submission: Submission, callback=None, **kwargs):
    contest = submission.contest
    cases = 'all' if contest.status > 0 else contest.run_tests_during_contest
    if cases != 'none':
        judge_submission_on_problem(submission, callback=callback, case=cases,
                                    status_private=contest.is_frozen)
    else:
        submission.status = submission.status_private = SubmissionStatus.SUBMITTED
        submission.save(update_fields=['status', 'status_private'])
        Thread(callback).start()




def update_problem_and_participant(contest_id, problem_id, user_id, accept_increment=0):
    """
    This function is used when judge result changed

    The three things we are going to do:
    1. update AC / Submit for ContestProblem
    2. update User (Participant) score
    3. update standings
    :param contest_id: the contest that is going to be affected
    :param problem_id: the problem that is going to be affected
    :param user_id: the user that is going to be affected
    :param accept_increment: does the submission increase AC or decrease?
    """
    contest = Contest.objects.get(pk=contest_id)
    with transaction.atomic():
        if accept_increment != 0:
            problem = contest.contestproblem_set.select_for_update().get(problem_id=problem_id)
            problem.add_accept(accept_increment)
            problem.save()

        participant, _ = contest.contestparticipant_set.select_for_update().\
            get_or_create(user__pk=user_id, defaults={'user': User.objects.get(pk=user_id), 'contest': contest})
        _update_participant(contest, participant)

    update_time = timezone.now()
    while (timezone.now() - contest.standings_update_time).seconds < 5:
        # Less than 5 seconds, and there has not been a newer refresh
        if contest.standings_update_time > update_time:
            return
        time.sleep(5)
        contest.refresh_from_db(fields=["standings_update_time"])

    _recalculate_rank(contest)
    contest.standings_update_time = timezone.now()
    contest.save(update_fields=["standings_update_time"])


def _update_participant(contest, participant):
    submissions = contest.submission_set.filter(author=participant.user).all()
    problems = contest.contestproblem_set.all()
    participant.score, participant.penalty, participant.html_cache = \
        recalculate_for_participant(contest, submissions, problems)
    participant.save(update_fields=["score", "penalty", "html_cache"])


def _update_header(contest):

    def _get_standings_header(rule, contest_problems):
        template = '<th class="col-width-{width}">{info}</th>'

        if rule == 'oi' or rule == 'oi2':
            res = template.format(width=3, info='=')
        else:
            res = template.format(width=2, info='=')
        if rule != 'oi2':
            res += template.format(width=5, info='Penalty')
        if rule != 'work':
            for contest_problem in contest_problems:
                res += template.format(width=4, info=contest_problem.identifier)
        return res

    contest.contest_header = _get_standings_header(contest.rule, contest.contestproblem_set.all())
    contest.save()


def update_contest(contest):
    with transaction.atomic():
        _update_header(contest)
        participants = contest.contestparticipant_set.select_for_update().all()
        for participant in participants:
            _update_participant(contest, participant)
    _recalculate_rank(contest)

    contest.standings_update_time = timezone.now()
    contest.save(update_fields=["standings_update_time"])


def _recalculate_rank(contest):

    def compare(a, b):
        if a.score == b.score:
            if a.penalty == b.penalty:
                return 0
            return -1 if a.penalty < b.penalty else 1
        return -1 if a.score > b.score else 1

    with transaction.atomic():
        participants = contest.contestparticipant_set.select_for_update().all()
        last_par = None
        index = 1
        for par in sorted(participants, key=cmp_to_key(compare)):
            if par.star:
                new_rank = None
            else:
                new_rank = index
                if last_par is not None and compare(last_par, par) == 0:
                    new_rank = last_par.rank
                last_par = par
                index += 1
            if new_rank != par.rank:
                par.rank = new_rank
                par.save(update_fields=["rank"])


def add_participant_with_invitation(contest_pk, invitation_pk, user):
    with transaction.atomic():
        contest = Contest.objects.get(pk=contest_pk)
        invitation = contest.contestinvitation_set.get(pk=invitation_pk)
        ContestParticipant.objects.create(user=user, comment=invitation.comment, contest=contest)
        invitation.delete()
    update_contest(contest)
