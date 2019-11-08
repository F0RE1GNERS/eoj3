from datetime import timedelta

from django.db import transaction

from problem.statistics import invalidate_problem
from submission.util import SubmissionStatus
from .models import Contest


def RANK_AS_DICT(x):
  return {
    "actual_rank": x.actual_rank,
    "rank": x.rank,
    "user": x.user_id,
    "penalty": x.penalty,
    "score": x.score,
    "detail": x.detail
  }


def get_submission_filter(contest: Contest, snapshot: timedelta, **kwargs):
  ret = contest.submission_set.filter(visible=True, **kwargs). \
    only("id", "status", "create_time", "author_id", "problem_id", "contest_id", "contest_time", "status_percent")
  if snapshot is not None:
    ret = ret.filter(contest_time__lte=snapshot).order_by("contest_time")
  else:
    ret = ret.order_by("create_time")
  return ret


def calculate_problems(contest: Contest, problems: list, snapshot: timedelta = None):
  """

  :param contest:
  :param problems: list of ContestProblems
  :param snapshot:
  :return:
  {
      <problem_id>: {
          user_ac: int,
          user_tot: int,
          ac: int,
          tot: int,
          first_yes: None/int
      }
  }
  """
  problem_ids = list(map(lambda p: p.problem_id, problems))
  ans = {problem_id: dict(user_ac=set(), user_tot=dict(), ac=0, tot=0, first_yes_time=None, first_yes_by=None)
         for problem_id in problem_ids}
  for submission in get_submission_filter(contest, snapshot, problem_id__in=problem_ids):
    pstat = ans[submission.problem_id]
    status = submission.status
    if SubmissionStatus.is_accepted(status):
      pstat["user_ac"].add(submission.author_id)
      pstat["ac"] += 1
      if submission.contest_time is not None and pstat["first_yes_time"] is None:
        pstat["first_yes_time"] = submission.contest_time
        pstat["first_yes_by"] = submission.author_id
    if (submission.author_id in pstat["user_tot"] and pstat["user_tot"][submission.author_id] <
        submission.status_percent) or submission.author_id not in pstat["user_tot"]:
      pstat["user_tot"][submission.author_id] = submission.status_percent
    pstat["tot"] += 1

  for p in problems:
    pstat = ans[p.problem_id]
    p.ac_user_count = len(pstat["user_ac"])
    p.total_user_count = len(pstat["user_tot"])
    p.ac_count = pstat["ac"]
    p.total_count = pstat["tot"]
    p.first_yes_time = pstat["first_yes_time"]
    p.first_yes_by = pstat["first_yes_by"]
    p.max_score = max(pstat["user_tot"].values()) if p.total_user_count > 0 else 0.0
    p.avg_score = sum(pstat["user_tot"].values()) / p.total_user_count if p.total_user_count > 0 else 0.0

  return ans


def calculate_participants(contest: Contest, participants: list, snapshot: timedelta = None):
  """
  :param contest
  :param participants: list of ContestParticipants
  :param snapshot: submissions in the first `snapshot` seconds will be effective
  :return
  {
      <user_id>: {
          penalty: int (seconds),
          score: int,
          is_confirmed: boolean
          detail: {
              <problem_id>: {
                  solved: boolean
                  attempt: int (submission count including the first accepted one),
                  score: int (individual score for each problem),
                  time: int (first accept solution time, in seconds),
                  partial: boolean
                  upsolve: int (positive for accepted, negative for unaccepted, score if partial)
              }
          }
      }
  }

  This will be saved to participants without writing to database (can do that outside)

  Penalty is the same for all rules: Every failed submission till the accepted one
  will add `penalty_counts` (default 1200) to it. And the accepted one will add the time (seconds) to it

  Score methods depend on the contest rule:
  1. ACM rule: individual score is all one, total score is solved problem number.
  2. OI rule: individual score is problem weight times the weight of cases passed (round to integer).
  3. CF rule: individual score is problem weight, but will only be available if the solution is by all means correct.

  How much percent one can get is a bit complicated:
  1) The total percent will decrease from contest beginning to contest end from 100% to 50%.
  2) Every failed submission will induce a 50-point loss to the score
  3) The final score, once accepted will not be lower than 30% of the total score.
  """

  user_ids = list(map(lambda p: p.user_id, participants))
  ans = {author_id: dict(detail=dict(), is_confirmed=False) for author_id in user_ids}
  contest_length = contest.length
  if contest_length is not None:
    contest_length = contest_length.total_seconds()

  for submission in get_submission_filter(contest, snapshot, author_id__in=user_ids):
    status = submission.status
    detail = ans[submission.author_id]['detail']

    author_id = submission.author_id
    ans[author_id]['is_confirmed'] = True

    detail.setdefault(submission.problem_id,
                      {'solved': False, 'attempt': 0, 'score': 0, 'time': 0,
                       'waiting': False, 'pass_time': '', 'partial': False, 'upsolve': 0})
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
    time = int(submission.contest_time.total_seconds()) if submission.contest_time is not None else 0
    score = 0
    EPS = 1E-2
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

    # upsolve submission
    if d['partial']:
      d['upsolve'] = max(d['upsolve'], score)
    elif d['upsolve'] <= 0:
      d['upsolve'] -= 1
      if SubmissionStatus.is_accepted(status):
        d['upsolve'] = abs(d['upsolve'])

    if contest.contest_type == 0 and submission.contest_time is None:
      d['upsolve_enable'] = True
      continue

    if contest.last_counts or not \
        (d['solved'] or (contest.scoring_method != 'oi' and d['score'] > 0 and d['score'] >= score)):
      # every submission has to be calculated in OI
      # We have to tell whether this is the best

      if not contest.last_counts:
        d['score'] = max(d['score'], score)
      else:
        d['score'] = score
      d['attempt'] += 1
      d.update(solved=SubmissionStatus.is_accepted(status), time=time, pass_time=pass_time)

  for v in ans.values():
    for p in v['detail']:
      d = v['detail'][p]
      if 'upsolve_enable' not in d:
        d['upsolve'] = 0
      else:
        d.pop('upsolve_enable', None)
    if contest.start_time is None:
      penalty = 0
    elif contest.scoring_method == 'oi':
      penalty = sum(map(lambda x: max(x['attempt'], 0) * contest.penalty_counts + x['time'],
                        v['detail'].values()))
    else:
      penalty = sum(map(lambda x: max(x['attempt'] - 1, 0) * contest.penalty_counts + x['time'],
                        filter(lambda x: x['solved'], v['detail'].values())))
    v.update(penalty=penalty, score=sum(map(lambda x: x['score'], v['detail'].values())))

  for p in participants:
    p.detail = ans[p.user_id]["detail"]
    p.score = ans[p.user_id]["score"]
    p.penalty = ans[p.user_id]["penalty"]
    p.is_confirmed = ans[p.user_id]["is_confirmed"]
  return ans


def participants_with_rank(contest: Contest, snapshot: timedelta = None):
  """
  :param contest:
  :param snapshot:
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
  if snapshot is not None:
    calculate_participants(contest, items, snapshot)
    items = sorted(list(items), key=lambda i: (not i.is_confirmed, -i.score, i.penalty, not i.star))
  last_item = None
  last_actual_item, last_actual_rank = None, 0

  actual_rank_counter = 1
  for idx, item in enumerate(items, start=1):
    if last_item and find_key(item) == find_key(last_item):
      claim_rank = last_item.rank
    else:
      claim_rank = idx

    if item.star:
      # starred
      actual_rank = 0
    else:
      if last_actual_item and find_key(item) == find_key(last_actual_item):
        actual_rank = last_actual_rank
      else:
        actual_rank = actual_rank_counter
      last_actual_rank, last_actual_item = actual_rank, item
      actual_rank_counter += 1

    item.rank = claim_rank
    item.actual_rank = actual_rank
    last_item = item
  return items


def get_contest_rank(contest: Contest, snapshot: timedelta = None):
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
  Refer to `calculate`.
  Rank is in order.
  """
  return list(map(RANK_AS_DICT, participants_with_rank(contest, snapshot)))


def get_participant_rank(contest: Contest, user_id):
  """
  Get rank in public standings

  Precondition: the contest should be ended FOR THE PARTICIPANT
  """
  for participant in participants_with_rank(contest):
    if participant.user_id == user_id:
      return participant.actual_rank
  return 0


def get_participant_score(contest: Contest, user_id, snapshot: timedelta = None):
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
  for participant in participants_with_rank(contest, snapshot):
    if participant.user_id == user_id:
      return RANK_AS_DICT(participant)
  return {}


def invalidate_contest_participant(contest: Contest, users=None):
  """
  :param contest:
  :param users:
      None: all participants
      int: primary key of a User instance
      list: list of primary keys of User instances
  :param sync:
  :return: None

  The process will get contest participant object from the user instances and save them to database
  """

  if users is None:
    participants = contest.contestparticipant_set.all()
  elif isinstance(users, int):
    participants = contest.contestparticipant_set.filter(user_id=users)
  elif isinstance(users, list):
    participants = contest.contestparticipant_set.filter(user_id__in=users)
  else:
    raise ValueError

  calculate_participants(contest, participants)

  with transaction.atomic():
    for p in participants:
      p.save(update_fields=["detail_raw", "score", "penalty", "is_confirmed"])


def invalidate_contest_problem(contest: Contest, problems=None):
  """
  :param contest:
  :param users:
      None: all participants
      int: primary key of a Problem instance
      list: list of primary keys of Problem instances
  :param sync:
  :return: None

  The process will get contest participant object from the user instances and save them to database
  """

  if problems is None:
    contest_problems = contest.contestproblem_set.all()
  elif isinstance(problems, int):
    contest_problems = contest.contestproblem_set.filter(problem_id=problems)
  elif isinstance(problems, list):
    contest_problems = contest.contestproblem_set.filter(problem_id__in=problems)
  else:
    raise ValueError

  calculate_problems(contest, contest_problems)

  with transaction.atomic():
    for p in contest_problems:
      p.save(update_fields=["ac_user_count", "total_user_count", "ac_count", "total_count",
                            "first_yes_time", "first_yes_by", "max_score", "avg_score"])


def invalidate_contest(contest: Contest):
  invalidate_contest_participant(contest)
  invalidate_contest_problem(contest)
  for problem in contest.contest_problem_list:
    invalidate_problem(problem.problem)
