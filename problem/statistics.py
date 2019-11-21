import logging
import traceback
from collections import Counter
from math import log10

import requests
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from tagging.models import TaggedItem, Tag

from problem.models import UserStatus, TagInfo, Problem
from submission.models import Submission
from submission.util import SubmissionStatus
from utils.permission import is_problem_manager

logger = logging.getLogger(__name__)

FORTNIGHT = 3600 * 24 * 7


def invalidate_problem(problem: Problem, save=True):
  query_list = list(problem.submission_set.filter(visible=True).values("author_id", "status"))
  ac_list = list(filter(lambda x: x["status"] == SubmissionStatus.ACCEPTED, query_list))
  problem.ac_user_count = len(set(map(lambda x: x["author_id"], ac_list)))
  problem.total_user_count = len(set(map(lambda x: x["author_id"], query_list)))
  problem.ac_count = len(ac_list)
  problem.total_count = len(query_list)
  reward_est = 5 - (2 * problem.ac_ratio + 3 * problem.ac_user_ratio) * min(log10(problem.ac_user_count + 1), 1.2) \
               + max(6 - 2 * log10(problem.ac_user_count + 1), 0)
  # reward_est = (max(reward_est, 0.) ** 2) / 10
  problem.reward = max(min(reward_est, 9.9), 0.1)
  for field in problem._meta.local_fields:  # pylint: disable=protected-access
    if field.name == "update_time":
      field.auto_now = False
  if save:
    problem.save(update_fields=["ac_user_count", "total_user_count", "ac_count", "total_count", "reward"])


def invalidate_user(user_id, contest_id=0):
  if contest_id is None:
    contest_id = 0
  if contest_id:
    invalidate_user(user_id)

  if contest_id:
    submission_filter = Submission.objects.filter(author_id=user_id, contest_id=contest_id).all()
  else:
    submission_filter = Submission.objects.filter(author_id=user_id).all()
  ac_filter = submission_filter.filter(status__in=[SubmissionStatus.ACCEPTED, SubmissionStatus.PRETEST_PASSED]). \
    only("problem_id", "id", "author_id", "status", "create_time").all()

  total_count = submission_filter.count()
  total_list = list(submission_filter.order_by().values_list("problem_id", flat=True).distinct())
  accept_count = ac_filter.count()
  accept_list = list(ac_filter.order_by().values_list("problem_id", flat=True).distinct())
  accept_diff = len(accept_list)

  us, created = UserStatus.objects.get_or_create(user_id=user_id, contest_id=contest_id,
                                                 defaults={
                                                   "total_count": total_count,
                                                   "total_list": ",".join(map(str, total_list)),
                                                   "ac_count": accept_count,
                                                   "ac_list": ",".join(map(str, accept_list)),
                                                   "ac_distinct_count": accept_diff
                                                 })

  new_solved = created or us.ac_count != accept_count
  if not created:
    us.total_count = total_count
    us.total_list = ",".join(map(str, total_list))
    us.ac_count = accept_count
    us.ac_list = ",".join(map(str, accept_list))
    us.ac_distinct_count = accept_diff
    us.save()

  next_problem_key = "NEXT_PROBLEM_{}".format(user_id)
  if contest_id == 0 and (new_solved or cache.get(next_problem_key) is None):
    try:
      already_ac_set = set()
      ac_time_ordered_list = []
      for ac_sub in ac_filter.order_by("create_time"):
        if ac_sub.id not in already_ac_set:
          already_ac_set.add(ac_sub.id)
          ac_time_ordered_list.append(ac_sub.id)
      predict_list = requests.post("http://{}/predict".format(settings.RECOMMENDATION_SERVICE_URL),
                                   json={"solved": accept_list}).json()
      cache.set(next_problem_key, predict_list["prediction"], timeout=FORTNIGHT)
    except:
      logger.warning(traceback.format_exc())
      cache.set(next_problem_key, [], timeout=FORTNIGHT)
  return us


def _get_or_invalidate_user(user_id, contest_id, field_name):
  try:
    return getattr(UserStatus.objects.get(user_id=user_id, contest_id=contest_id), field_name)
  except:
    return getattr(invalidate_user(user_id, contest_id), field_name)


def get_accept_submission_count(user_id, contest_id=0):
  return _get_or_invalidate_user(user_id, contest_id, "ac_count")


def get_accept_problem_count(user_id, contest_id=0):
  return _get_or_invalidate_user(user_id, contest_id, "ac_distinct_count")


def get_accept_problem_list(user_id, contest_id=0):
  t = _get_or_invalidate_user(user_id, contest_id, "ac_list")
  if not t:
    return []
  return list(map(int, t.split(',')))


def get_total_submission_count(user_id, contest_id=0):
  return _get_or_invalidate_user(user_id, contest_id, "total_count")


def get_attempted_problem_list(user_id, contest_id=0):
  t = _get_or_invalidate_user(user_id, contest_id, "total_list")
  if not t:
    return []
  return list(map(int, t.split(',')))


def is_problem_accepted(user, problem):
  return is_problem_manager(user, problem) or (user.is_authenticated and
                                               user.submission_set.filter(problem=problem,
                                                                          status=SubmissionStatus.ACCEPTED).exists())


def get_children_tag_id(tag: int = -1):
  tags = {tag}
  while True:
    adds = set(TagInfo.objects.filter(parent_id__in=tags).values_list("tag_id", flat=True))
    if (adds & tags) == adds:
      break
    tags |= adds
  return tags


def tags_stat(user_id):
  all_count = {t.id: t.count for t in Tag.objects.usage_for_model(Problem, counts=True)}
  accept_counter = Counter()
  accept_list = get_accept_problem_list(user_id)
  for tag_id in TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem)) \
      .filter(object_id__in=accept_list).values_list("tag_id", flat=True):
    accept_counter[tag_id] += 1
  return {tag_id: (accept_counter[tag_id], cnt) for tag_id, cnt in all_count.items()}


def get_next_k_recommended_problems(user_id, problem_ids, k=5):
  try:
    problem_list = []
    for _ in range(3):  # retry 3 times
      problem_list = cache.get("NEXT_PROBLEM_{}".format(user_id))
      if problem_list is None:
        invalidate_user(user_id)
    if problem_list is None:
      logger.error("Out of retry count")
      problem_list = []
    problem_ids = set(problem_ids)
    ret = []
    for prob in problem_list:
      if prob in problem_ids:
        ret.append(prob)
      if len(ret) >= k:
        break
    if len(ret) < k:
      logger.warning("There isn't enough problems to recommend")
    return ret
  except:
    logger.warning(traceback.format_exc())
    return []
