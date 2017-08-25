from submission.models import SubmissionStatus, Submission
from .models import Contest, ContestParticipant
from account.models import User
from django.core.cache import cache
from random import uniform


PARTICIPANT_RANK_DETAIL = 'c{contest}_u{user}_rank_detail'
PARTICIPANT_RANK_DETAIL_PRIVATE = 'c{contest}_u{user}_rank_detail_private'
PARTICIPANT_RANK = 'c{contest}_u{user}_rank'
PARTICIPANT_RANK_LIST = 'c{contest}_rank_list'
FORTNIGHT = 86400 * 14


def recalculate_for_participant(contest: Contest, user_id: int, privilege=False):
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
    for submission in contest.submission_set.filter(author=user_id).only("status", "status_private", "contest_id",
                                                                         "problem_id", "author_id",
                                                                         "create_time").order_by("create_time"):
        contest_problem = contest.get_contest_problem(submission.problem_id)
        if not contest_problem:  # This problem has been probably deleted
            continue
        detail.setdefault(submission.problem_id,
                          {'solved': False, 'attempt': 0, 'score': 0, 'first_blood': False, 'time': 0})
        d = detail[submission.problem_id]
        status = submission.status_private if privilege else submission.status
        if not SubmissionStatus.is_penalty(status):
            continue  # This is probably CE or SE ...
        time = get_penalty(contest.start_time, submission.create_time)
        score = 0
        if contest.scoring_method == 'oi':
            score = int(submission.status_percent / 100 * contest_problem.weight)
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
                                         status=SubmissionStatus.ACCEPTED).last().author_id == user_id:
            d.update(first_blood=True)

    return {
        'penalty': sum(map(lambda x: max(x['attempt'] - 1, 0) * 1200 + x['time'], detail.values())),
        'score': sum(map(lambda x: x['score'], detail.values())),
        'detail': detail
    }


def get_contest_rank(contest: Contest, privilege=False):
    # TODO: support slice
    lst = get_contest_rank_list(contest, privilege=privilege)
    details = get_all_contest_participants_detail(contest, privilege=privilege)
    for idx, item in enumerate(lst):
        rank = item[1]
        lst[idx] = details[item[0]]
        lst[idx].update(rank=rank, user=item[0])
    return lst


def get_contest_user_ids(contest: Contest):
    return list(ContestParticipant.objects.filter(contest=contest).order_by().
                values_list("user_id", flat=True))


def get_all_contest_participants_detail(contest: Contest, users=None, privilege=False):
    cache_template = PARTICIPANT_RANK_DETAIL_PRIVATE if privilege else PARTICIPANT_RANK_DETAIL
    timeout = 60 if privilege else FORTNIGHT
    contest_users = users if users else get_contest_user_ids(contest)
    cache_names = list(map(lambda x: cache_template.format(contest=contest.pk, user=x), contest_users))
    cache_res = cache.get_many(cache_names)
    ans = dict()
    for user in contest_users:
        cache_name = cache_template.format(contest=contest.pk, user=user)
        if cache_name not in cache_res.keys():
            cache.set(cache_name, recalculate_for_participant(contest, user, privilege), timeout * uniform(0.6, 1))
            ans[user] = cache.get(cache_name)
        else:
            ans[user] = cache_res[cache_name]
    return ans


def get_contest_rank_list(contest: Contest, privilege=False):
    def _calculate():

        def find_key(tup):
            if contest.penalty_counts:
                return tup[1]['score'], -tup[1]['penalty']
            else:
                return tup[1]['score']

        items = sorted(get_all_contest_participants_detail(contest, privilege).items(),
                       key=find_key, reverse=True)
        ans = []  # ans = [(user_id, rank), ...]
        last_item = None
        for idx, item in enumerate(items, start=1):
            if last_item and find_key(item) == find_key(last_item):
                ans.append((item[0], ans[-1][1]))
            else:
                ans.append((item[0], idx))
            last_item = item
        return ans

    if not privilege:
        # Try to use cache
        cache_name = PARTICIPANT_RANK_LIST.format(contest=contest.pk)
        t = cache.get(cache_name)
        if t is None:
            t = _calculate()
            cache.set(cache_name, t, FORTNIGHT * uniform(0.6, 1))
            d = {PARTICIPANT_RANK.format(contest=contest.pk, user=user): rank for user, rank in t}
            cache.set_many(d, FORTNIGHT * uniform(0.6, 1))
        return t
    else:
        return _calculate()


def get_participant_rank(contest: Contest, user_id):
    """
    Get rank in public standings
    """
    cache_name = PARTICIPANT_RANK.format(contest=contest.pk, user=user_id)
    t = cache.get(cache_name)
    if t is None:
        rank = 0
        get_contest_rank_list(contest)
        t = cache.get(cache_name)
        if t is not None:
            rank = t
    else:
        rank = t
    return rank


def invalidate_contest_participant(contest: Contest, user_id):
    cache.delete(PARTICIPANT_RANK_DETAIL.format(contest=contest.pk, user=user_id))
    cache.delete(PARTICIPANT_RANK_LIST.format(contest=contest.pk))


def invalidate_contest(contest: Contest):
    contest_users = get_contest_user_ids(contest)
    cache.delete_many(list(map(lambda x: PARTICIPANT_RANK_DETAIL.format(contest=contest.pk, user=x), contest_users)))
    cache.delete_many(list(map(lambda x: PARTICIPANT_RANK_DETAIL_PRIVATE.format(contest=contest.pk, user=x), contest_users)))
    cache.delete(PARTICIPANT_RANK_LIST.format(contest=contest.pk))
