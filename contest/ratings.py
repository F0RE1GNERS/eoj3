from math import sqrt

from contest.statistics import get_contest_rank
from contest.models import ContestUserRating, Contest


INITIAL_RATING = 1500


class RatingContestant:
    def __init__(self, user: int, rank: float, points: float, rating: int):
        self.user = int(user)
        self.rank = float(rank)
        self.points = float(points)
        self.rating = int(rating)

    def __repr__(self):
        return 'RatingContestant: %s' % self.__dict__


def get_previous_ratings(contest: Contest):
    """
    :return: Map<User_id, Rating>
    """
    contest_participants = contest.participants_ids
    result = {}
    for rating_record in ContestUserRating.objects.filter(user_id__in=contest.participants_ids):
        if rating_record.user_id not in result:
            result[rating_record.user_id] = rating_record.rating
    for participant in contest_participants:
        if participant not in result:
            result[participant] = INITIAL_RATING
    return result


def calculate_rating_changes(contest: Contest):
    clear_previous_ratings(contest)
    previous_ratings = get_previous_ratings(contest)
    standing_rows = get_contest_rank(contest)
    contestants = []
    query_solved, query_rank = {}, {}
    for standing_row in standing_rows:
        if not standing_row.get("actual_rank"):
            continue
        user, rank = standing_row["user"], standing_row["actual_rank"]
        contestants.append(RatingContestant(user, rank, standing_row["score"], previous_ratings[user]))
        query_solved[user] = sum(map(lambda detail: int(detail["solved"]), standing_row["detail"].values()))
        query_rank[user] = rank
    _process(contestants)

    new_ratings = list(map(lambda contestant: ContestUserRating(rating=contestant.rating + contestant.delta,
                                                                user_id=contestant.user,
                                                                contest=contest,
                                                                modified=contest.end_time,
                                                                solved=query_solved[contestant.user],
                                                                rank=query_rank[contestant.user]), contestants))
    ContestUserRating.objects.bulk_create(new_ratings)


def clear_previous_ratings(contest: Contest):
    ContestUserRating.objects.filter(contest=contest).delete()


def _get_elo_win_probability(a: RatingContestant, b: RatingContestant):
    """
    :param a:
    :param b:
    :return: probability that a wins b
    """
    return 1 / (1 + pow(10, (b.rating - a.rating) / 400))


def _get_seed(contestants: list, rating: int):
    extra_contestant = RatingContestant(0, 0, 0, rating)
    result = 1 + sum(map(lambda other: _get_elo_win_probability(other, extra_contestant), contestants))
    return result


def _get_rating_to_rank(contestants: list, rank: float):
    left, right = 1, 8000
    while right - left > 1:
        mid = (left + right) // 2
        if _get_seed(contestants, mid) < rank:
            right = mid
        else:
            left = mid
    return left


def _sort_by_points_desc(contestants: list):
    contestants.sort(key=lambda contestant: contestant.points, reverse=True)


def _sort_by_rating_desc(contestants: list):
    contestants.sort(key=lambda contestant: contestant.rating, reverse=True)


def _reassign_ranks(contestants: list):
    _sort_by_points_desc(contestants)
    for contestant in contestants:
        contestant.rank = 0
        contestant.delta = 0
    first = 0
    for i in range(1, len(contestants)):
        if contestants[i].points < contestants[first].points:
            for j in range(first, i):
                contestants[j].rank = i
            first = i

    rank = float(len(contestants))
    for j in range(first, len(contestants)):
        contestants[j].rank = rank


def _process(contestants):
    if len(contestants) == 0:
        return
    _reassign_ranks(contestants)
    for a in contestants:
        a.seed = 1
        for b in contestants:
            if a.user != b.user:
                a.seed += _get_elo_win_probability(b, a)
    for contestant in contestants:
        mid_rank = sqrt(contestant.rank * contestant.seed)
        contestant.need_rating = _get_rating_to_rank(contestants, mid_rank)
        contestant.delta = int((contestant.need_rating - contestant.rating) / 2)

    _sort_by_rating_desc(contestants)

    sum_delta = sum(map(lambda c: c.delta, contestants))
    inc = -int(sum_delta / len(contestants)) - 1
    for contestant in contestants:
        contestant.delta += inc

    zero_sum_count = min(int(4 * round(sqrt(len(contestants)))), len(contestants))
    sum_delta = sum(map(lambda c: c.delta, contestants[:zero_sum_count]))
    inc = min(max(-int(sum_delta / zero_sum_count), -10), 0)
    for contestant in contestants:
        contestant.delta += inc

    _validate_deltas(contestants)


def _validate_deltas(contestants):
    _sort_by_points_desc(contestants)
    for i in range(len(contestants)):
        for j in range(i + 1, len(contestants)):
            if contestants[i].rating > contestants[j].rating and \
                                    contestants[i].rating + contestants[i].delta >= contestants[j].rating + contestants[j].delta:
                raise ValueError("First rating invariant failed: %d vs. %d." % (contestants[i].user, contestants[j].user))
            if contestants[i].rating < contestants[j].rating and \
                            contestants[i].delta >= contestants[j].delta:
                raise ValueError(
                    "Second rating invariant failed: %d vs. %d." % (contestants[i].user, contestants[j].user))
