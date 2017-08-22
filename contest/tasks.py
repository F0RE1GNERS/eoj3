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


PARTICIPANT_RANK_DETAIL = 'c{contest}_u{user}_rank_detail'
PARTICIPANT_RANK_DETAIL_PRIVATE = 'c{contest}_u{user}_rank_detail_private'
PARTICIPANT_RANK = 'c{contest}_u{user}_rank'
PARTICIPANT_RANK_LIST = 'c{contest}_rank_list'


def recalculate_for_participant(contest: Contest, user: User, privilege=False):
    """
    :param contest
    :param user
    :param privilege: privilege will cause the calculation works for all submissions even after board frozen
    :return {
        penalty: int (seconds),
        score: int,
        detail: {
            <problem_id>: {
                solved: boolean
                attempt: int (submission count including the first accepted one),
                score: int (individual score for each problem),
                time: int (first accept solution time, in seconds),
                first_blood: boolean
            }
        }
    }

    Penalty is the same for all rules: Every failed submission till the accepted one
    will add 1200 to it. And the accepted one will add the time (seconds) to it

    Score methods depend on the contest rule:
    1. ACM rule: individual score is all one, total score is solved problem number.
    2. OI rule: individual score is problem weight times the weight of cases passed (round to integer).
    3. CF rule: individual score is problem weight, but will only be available if the solution is by all means correct.

    How much percent one can get is a bit complicated:
    1) The total percent will decrease from contest beginning to contest end from 100% to 50%.
    2) Every failed submission will induce a 50-point loss to the score
    3) The final score, once accepted will not be lower than 30% of the total score.
    """

    def get_penalty(start_time, submit_time):
        """
        :param start_time: time in DateTimeField
        :param submit_time: time in DateTimeField
        :return: penalty in seconds
        """
        return max(int((submit_time - start_time).total_seconds()), 0)

    detail = {}
    contest_length = get_penalty(contest.start_time, contest.end_time)
    for submission in contest.submission_set.filter(author=user).only("status", "status_private", "contest_id",
                                                                      "problem_id", "author_id",
                                                                      "create_time").order_by("create_time"):
        contest_problem = contest.get_contest_problem(submission.problem_id)
        if not contest_problem:  # This problem has been probably deleted
            continue
        detail.setdefault(submission.problem_id,
                          {'solved': False, 'attempt': 0, 'score': -1, 'first_blood': False, 'time': 0})
        d = detail[submission.problem_id]
        status = submission.status_private if privilege else submission.status
        if not SubmissionStatus.is_penalty(status):
            continue  # This is probably CE or SE ...
        time = get_penalty(contest.start_time, submission.create_time)
        score = 0
        if contest.scoring_method == 'oi':
            score = int(submission.partial_score / submission.total_score * contest_problem.weight)
        elif contest.scoring_method == 'acm' and SubmissionStatus.is_accepted(status):
            score = 1
        elif contest.scoring_method == 'cf' and SubmissionStatus.is_accepted(status):
            score = int(min(contest_problem.weight * 0.3,
                            contest_problem.weight * (1 - 0.5 * time / contest_length) - d['attempt'] * 50))
        if not contest.last_counts and (d['solved'] or d['score'] >= score):
            # We have to tell whether this is the best
            continue

        d['attempt'] += 1
        d.update(solved=SubmissionStatus.is_accepted(status), score=score, time=time)
        if contest.submission_set.filter(problem_id=submission.problem_id,
                                         status=SubmissionStatus.ACCEPTED).last():
            d.update(first_blood=True)

    return {
        'penalty': sum(map(lambda x: max(x['attempt'] - 1, 0) * 1200 + x['time'], detail.values())),
        'score': sum(map(lambda x: x['score'], detail.values())),
        'detail': detail
    }


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
