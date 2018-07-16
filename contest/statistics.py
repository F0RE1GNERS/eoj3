import json
from threading import Thread

from django.core.cache import cache
from django.db import transaction

from submission.models import SubmissionStatus
from .models import Contest

CONTEST_FIRST_YES = "contest_first_yes_{}"

def RANK_AS_DICT(x):
    return {
        "actual_rank": x.actual_rank,
        "rank": x.rank,
        "user": x.user_id,
        "penalty": x.penalty,
        "score": x.score,
        "detail": x.detail
    }


def get_penalty(start_time, submit_time):
    """
    :param start_time: time in DateTimeField
    :param submit_time: time in DateTimeField
    :return: penalty in seconds
    """
    return max(int((submit_time - start_time).total_seconds()), 0)


def recalculate_for_participants(contest: Contest, user_ids: list):
    """
    :param contest
    :param user_ids
    :param privilege: privilege will cause the calculation works for all submissions even after board frozen
    :return {
        <user_id>: {
            penalty: int (seconds),
            score: int,
            detail: {
                <problem_id>: {
                    solved: boolean
                    attempt: int (submission count including the first accepted one),
                    score: int (individual score for each problem),
                    time: int (first accept solution time, in seconds),
                    first_blood: boolean
                    partial: boolean
                }
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

    ans = {author_id: dict(detail=dict()) for author_id in user_ids}
    contest_length = get_penalty(contest.start_time, contest.end_time)
    first_yes = get_first_yes(contest, no_invalidate=True)

    for submission in contest.submission_set.filter(author_id__in=user_ids).defer(
            "code", "status_message", "status_detail").order_by("create_time"):
        status = submission.status
        detail = ans[submission.author_id]['detail']
        detail.setdefault(submission.problem_id,
                          {'solved': False, 'attempt': 0, 'score': 0, 'first_blood': False, 'time': 0,
                           'waiting': False, 'pass_time': '', 'partial': False})
        d = detail[submission.problem_id]
        if not SubmissionStatus.is_judged(submission.status):
            d['waiting'] = True
            continue
        if SubmissionStatus.is_scored(submission.status):
            d['partial'] = True

        if not SubmissionStatus.is_penalty(status):
            continue  # This is probably CE or SE ...
        contest_problem = contest.get_contest_problem(submission.problem_id)
        if not contest_problem:  # This problem has been probably deleted
            continue

        pass_time = str(submission.create_time.strftime('%Y-%m-%d %H:%M:%S'))
        time = get_penalty(contest.start_time, submission.create_time)
        score = 0
        if contest.scoring_method == 'oi' or contest.scoring_method == "subtask":
            submission.contest_problem = contest_problem
            score = submission.status_score
        elif contest.scoring_method == 'acm' and SubmissionStatus.is_accepted(status):
            score = 1
        elif contest.scoring_method == 'cf' and SubmissionStatus.is_accepted(status):
            score = int(max(contest_problem.weight * 0.3,
                            contest_problem.weight * (1 - 0.5 * time / contest_length) - d['attempt'] * 50) + EPS)
        elif contest.scoring_method == 'tcmtime' and SubmissionStatus.is_accepted(status):
            score = contest_problem.weight
        if not contest.last_counts and (d['solved'] or (d['score'] > 0 and d['score'] >= score)):
            # We have to tell whether this is the best
            continue

        d['attempt'] += 1
        d.update(solved=SubmissionStatus.is_accepted(status), score=score, time=time, pass_time=pass_time)
        if first_yes.get(submission.problem_id) and first_yes[submission.problem_id]['author'] == submission.author_id:
            d['first_blood'] = True

    for v in ans.values():
        v.update(penalty=sum(map(lambda x: max(x['attempt'] - 1, 0) * 1200 + x['time'],
                                 filter(lambda x: x['solved'], v['detail'].values()))),
                 score=sum(map(lambda x: x['score'], v['detail'].values())))
    return ans


def participants_with_rank(contest: Contest):
    """
    :param contest:
    :param privilege:
    :return: contest participants objects with 2 additional fields:
        - actual_rank
        - rank

    actual_rank is the rank considering starred participants
    """
    def find_key(t):
        if contest.penalty_counts:
            return t.score, -t.penalty
        else:
            return t.score

    items = contest.contestparticipant_set.all()
    last_item = None
    last_actual_item, last_actual_rank = None, 0

    actual_rank_counter = 1
    for idx, item in enumerate(items, start=1):
        if last_item and find_key(item) == find_key(last_item):
            claim_rank = last_item.rank
        else: claim_rank = idx

        if item.star:
            # starred
            actual_rank = 0
        else:
            if last_actual_item and find_key(item) == find_key(last_actual_item):
                actual_rank = last_actual_rank
            else: actual_rank = actual_rank_counter
            last_actual_rank, last_actual_item = actual_rank, item
            actual_rank_counter += 1

        item.rank = claim_rank
        item.actual_rank = actual_rank
        last_item = item
    return items


def get_contest_rank(contest: Contest):
    """
    :param contest
    :return [
        {
            actual_rank: int
            rank: int
            user: user_id
            penalty: ...
            score: ...
            detail: ...
        },
        ...,
    ]
    Refer to `recalculate_for_participants`.
    Rank is in order.
    """
    return list(map(RANK_AS_DICT, participants_with_rank(contest)))


def get_participant_rank(contest: Contest, user_id):
    """
    Get rank in public standings
    """
    for participant in participants_with_rank(contest):
        if participant.user_id == user_id:
            return participant.actual_rank
    return 0


def get_participant_score(contest: Contest, user_id):
    """
    Return full record of score

    :param contest:
    :param user_id:
    :return:
        {
            actual_rank: int
            rank: int
            user: user_id
            penalty: ...
            score: ...
            detail: ...
        }
    """
    for participant in participants_with_rank(contest):
        if participant.user_id == user_id:
            return RANK_AS_DICT(participant)
    return {}


def get_first_yes(contest: Contest, no_invalidate=False):
    """
    :param contest:
    :param no_invalidate: set this to bool to disable invalidate action (prevent endless recursion)
    :return: {
        <problem_id>: {
            time: <int>
            author: <int>
        }
    }
    """
    cache_name = CONTEST_FIRST_YES.format(contest.pk)
    t = cache.get(cache_name)
    if t is None:
        t = dict()
        for contest_problem in contest.contest_problem_list:
            first_accepted_sub = contest.submission_set.filter(problem_id=contest_problem.problem_id,
                                                               status__in=[SubmissionStatus.ACCEPTED,
                                                                           SubmissionStatus.PRETEST_PASSED]).\
                defer("code", "status_message", "status_detail").last()
            if first_accepted_sub:
                first_accepted = dict(time=get_penalty(contest.start_time, first_accepted_sub.create_time),
                                      author=first_accepted_sub.author_id)
                if not no_invalidate:
                    invalidate_contest_participant(contest, first_accepted_sub.author_id)
            else:
                first_accepted = None
            t[contest_problem.problem_id] = first_accepted
        cache.set(cache_name, t, 60)  # 60 seconds
    return t


def invalidate_contest_participant(contest: Contest, users=None, sync=False):
    if contest.is_frozen:
        return

    def invalidate_process():
        with transaction.atomic():
            if users is None:
                user_ids = contest.participants_ids
            elif isinstance(users, int):
                user_ids = [users]
            elif isinstance(users, list):
                user_ids = users
            else:
                raise ValueError
            intermediate = recalculate_for_participants(contest, user_ids)
            for user_id, res in intermediate.items():
                user = contest.contestparticipant_set.get(user_id=user_id)
                user.detail = res["detail"]
                user.score = res["score"]
                user.penalty = res["penalty"]
                user.save(update_fields=["detail_raw", "score", "penalty"])

    if sync:
        invalidate_process()
    else:
        Thread(target=invalidate_process).start()


def invalidate_contest(contest: Contest, sync=False):
    if contest.is_frozen:
        return

    invalidate_contest_participant(contest, sync=sync)
    cache.delete(CONTEST_FIRST_YES.format(contest.pk))
