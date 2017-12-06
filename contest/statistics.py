from threading import Thread
from time import sleep

from submission.models import SubmissionStatus, Submission
from .models import Contest, ContestParticipant
from account.models import User
from django.core.cache import cache
from random import uniform

PARTICIPANT_RANK_DETAIL = 'c{contest}_u{user}_rank_detail'
PARTICIPANT_RANK_DETAIL_PRIVATE = 'c{contest}_u{user}_rank_detail_private'
PARTICIPANT_RANK = 'c{contest}_u{user}_rank'
PARTICIPANT_RANK_LIST = 'c{contest}_rank_list'
CONTEST_FIRST_YES = 'c{contest}_first_yes'
FORTNIGHT = 86400 * 14


def get_penalty(start_time, submit_time):
    """
    :param start_time: time in DateTimeField
    :param submit_time: time in DateTimeField
    :return: penalty in seconds
    """
    return max(int((submit_time - start_time).total_seconds()), 0)


def recalculate_for_participants(contest: Contest, user_ids: list, privilege=False):
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
    first_yes = get_first_yes(contest)

    for submission in contest.submission_set.filter(author_id__in=user_ids).only("status", "status_private",
                                                                                 "contest_id",
                                                                                 "problem_id", "author_id",
                                                                                 "create_time").order_by("create_time"):
        status = submission.status_private if privilege else submission.status
        detail = ans[submission.author_id]['detail']
        detail.setdefault(submission.problem_id,
                          {'solved': False, 'attempt': 0, 'score': 0, 'first_blood': False, 'time': 0,
                           'waiting': False, 'pass_time': ''})
        d = detail[submission.problem_id]
        if not SubmissionStatus.is_judged(submission.status):
            d['waiting'] = True
            continue
        if not SubmissionStatus.is_penalty(status):
            continue  # This is probably CE or SE ...
        contest_problem = contest.get_contest_problem(submission.problem_id)
        if not contest_problem:  # This problem has been probably deleted
            continue

        pass_time = str(submission.create_time.strftime('%Y-%m-%d %H:%M:%S'))
        time = get_penalty(contest.start_time, submission.create_time)
        score = 0
        if contest.scoring_method == 'oi':
            score = int(submission.status_percent / 100 * contest_problem.weight)
        elif contest.scoring_method == 'acm' and SubmissionStatus.is_accepted(status):
            score = 1
        elif contest.scoring_method == 'cf' and SubmissionStatus.is_accepted(status):
            score = int(max(contest_problem.weight * 0.3,
                            contest_problem.weight * (1 - 0.5 * time / contest_length) - d['attempt'] * 50))
        if not contest.last_counts and (d['solved'] or (d['score'] > 0 and d['score'] >= score)):
            # We have to tell whether this is the best
            continue

        d['attempt'] += 1
        d.update(solved=SubmissionStatus.is_accepted(status), score=score, time=time, pass_time=pass_time)
        if first_yes[submission.problem_id] and first_yes[submission.problem_id]['author'] == submission.author_id:
            d['first_blood'] = True

    for v in ans.values():
        v.update(penalty=sum(map(lambda x: max(x['attempt'] - 1, 0) * 1200 + x['time'],
                                 filter(lambda x: x['solved'], v['detail'].values()))),
                 score=sum(map(lambda x: x['score'], v['detail'].values())))
    return ans


def get_contest_rank(contest: Contest, privilege=False):
    # TODO: support slice
    lst = get_contest_rank_list(contest, privilege=privilege)
    details = get_all_contest_participants_detail(contest, privilege=privilege)
    for idx, item in enumerate(lst):
        rank = item[1]
        lst[idx] = details[item[0]]
        lst[idx].update(rank=rank, user=item[0])
    return lst


def get_all_contest_participants_detail(contest: Contest, users=None, privilege=False):
    cache_template = PARTICIPANT_RANK_DETAIL_PRIVATE if privilege else PARTICIPANT_RANK_DETAIL
    timeout = 60 if privilege else FORTNIGHT
    contest_users = users if users else contest.participants_ids
    cache_names = list(map(lambda x: cache_template.format(contest=contest.pk, user=x), contest_users))
    cache_res = cache.get_many(cache_names)
    ans = dict()
    second_attempt = []
    for user in contest_users:
        cache_name = cache_template.format(contest=contest.pk, user=user)
        if cache_name not in cache_res.keys():
            second_attempt.append(user)
        else:
            ans[user] = cache_res[cache_name]
    if second_attempt:
        ans2 = recalculate_for_participants(contest, second_attempt, privilege)
        cache.set_many({cache_template.format(contest=contest.pk, user=user_id): val for user_id, val in ans2.items()},
                       timeout * uniform(0.8, 1))
        ans.update(ans2)
    return ans


def get_contest_rank_list(contest: Contest, privilege=False):
    def _calculate():

        def find_key(tup):
            if contest.penalty_counts:
                return tup[1]['score'], -tup[1]['penalty']
            else:
                return tup[1]['score']

        items = sorted(get_all_contest_participants_detail(contest, privilege=privilege).items(),
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


def get_first_yes(contest: Contest):
    cache_name = CONTEST_FIRST_YES.format(contest=contest.pk)
    t = cache.get(cache_name)
    if t is None:
        t = dict()
        for contest_problem in contest.contest_problem_list:
            first_accepted_sub = contest.submission_set.filter(problem_id=contest_problem.problem_id,
                                                               status=SubmissionStatus.ACCEPTED).only(
                'contest_id', 'problem_id', 'status', 'create_time').last()
            if first_accepted_sub:
                first_accepted = dict(time=get_penalty(contest.start_time, first_accepted_sub.create_time),
                                      author=first_accepted_sub.author_id)
                invalidate_contest_participant(contest, first_accepted_sub.author_id)
            else:
                first_accepted = None
            t[contest_problem.problem_id] = first_accepted
        cache.set(cache_name, t, 60)  # 60 seconds
    return t


def invalidate_contest_participant(contest: Contest, user_id):
    def invalidate_process(timeout):
        if timeout > 0:
            sleep(timeout)
        cache.delete(PARTICIPANT_RANK_DETAIL.format(contest=contest.pk, user=user_id))
        cache.delete(PARTICIPANT_RANK_LIST.format(contest=contest.pk))

    invalidate_process(0)
    Thread(target=invalidate_process, args=(60, )).start()
    # refresh after one minute to recalculate for possible mistake due to lack of locks


def invalidate_contest(contest: Contest):
    contest_users = contest.participants_ids
    cache.delete_many(list(map(lambda x: PARTICIPANT_RANK_DETAIL.format(contest=contest.pk, user=x), contest_users)))
    cache.delete_many(
        list(map(lambda x: PARTICIPANT_RANK_DETAIL_PRIVATE.format(contest=contest.pk, user=x), contest_users)))
    cache.delete(PARTICIPANT_RANK_LIST.format(contest=contest.pk))
    cache.delete(CONTEST_FIRST_YES.format(contest=contest.pk))
