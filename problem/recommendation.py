import functools
import random
from collections import Counter
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from tagging.models import Tag, TaggedItem

from problem.commons.problem_list_helper import get_problems_entity_list_helper, attach_personal_solve_info, \
  no_tags_entity_list_helper
from problem.models import Problem
from problem.statistics import get_accept_problem_list, tags_stat
from submission.models import Submission


def use_cached_result(func):
  @functools.wraps(func)
  def wrapper(user_id):
    key = func.__name__ + "_" + str(user_id)
    val = cache.get(key)
    if val is not None:
      return val
    val = func(user_id)
    cache.set(key, val, 60)
    return val

  return wrapper


def trending_problems(user_id):
  counter = Counter()
  for sub in Submission.objects.filter(visible=True, create_time__gte=datetime.now() - timedelta(days=3)). \
      values("id", "problem_id", "author_id").distinct():
    counter[sub["problem_id"]] += 1
  problems = []
  for k, v in counter.most_common():
    try:
      prob = Problem.objects.get(id=k, visible=True)
      prob.trending = v
      problems.append(prob)
      if len(problems) >= 5:
        break
    except Problem.DoesNotExist:
      pass
  attach_personal_solve_info(problems, user_id)
  return problems


@no_tags_entity_list_helper
@use_cached_result
def unsolved_problems(user_id):
  unsolved_problem_id = list(Problem.objects.filter(ac_user_count=0, visible=True).values_list("id", flat=True))
  random.shuffle(unsolved_problem_id)
  return unsolved_problem_id[:5]


def random_unsolved_problems_with_difficulty(solved_list, k):
  problem_ids = list(Problem.objects.filter(visible=True, reward__gte=k - 0.5, reward__lte=k + 1.5). \
              exclude(pk__in=solved_list).values_list("id", flat=True))
  random.shuffle(problem_ids)
  return problem_ids[:5]


@no_tags_entity_list_helper
@use_cached_result
def hard_problems(user_id):
  ac_list = get_accept_problem_list(user_id)
  ac_difficulty = sorted(list(Problem.objects.filter(id__in=ac_list).values_list("reward", flat=True)), reverse=True)
  try:
    ac_difficulty = ac_difficulty[:int(0.2 * len(ac_difficulty))]
    difficulty_level = sum(ac_difficulty) / len(ac_difficulty)
  except:
    difficulty_level = 8
  return random_unsolved_problems_with_difficulty(ac_list, difficulty_level)


@no_tags_entity_list_helper
@use_cached_result
def med_problems(user_id):
  ac_list = get_accept_problem_list(user_id)
  ac_difficulty = sorted(list(Problem.objects.filter(id__in=ac_list).values_list("reward", flat=True)), reverse=True)
  try:
    difficulty_level = sum(ac_difficulty) / len(ac_difficulty)
  except:
    difficulty_level = 4
  if len(ac_difficulty) < 100:
    difficulty_level *= len(ac_difficulty) / 200 + 0.5
  return random_unsolved_problems_with_difficulty(ac_list, difficulty_level)


def select_with_tags(user_id, tags_record):
  user_accept_all = set(get_accept_problem_list(user_id))
  ret = set()
  for k, (done, _) in tags_record:
    available_problems = TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem)) \
        .filter(tag_id=k).values_list("object_id", flat=True)
    accept_problems = set(available_problems) & user_accept_all
    if not accept_problems:
      ref_reward = 0.
    else:
      accept_problems_reward = Problem.objects.filter(id__in=accept_problems) \
          .order_by("-reward").values_list("reward", flat=True)[:3]
      ref_reward = sum(accept_problems_reward) / len(accept_problems)
    retrieve_list = Problem.objects.filter(reward__gte=ref_reward, reward__lte=ref_reward + 2, visible=True,
                                           id__in=set(available_problems) - user_accept_all) \
        .values_list("id", flat=True)
    if retrieve_list:
      ret.add(random.choice(retrieve_list))
    if len(ret) >= 5:
      break
  return list(ret)


@get_problems_entity_list_helper
@use_cached_result
def familiar_problems(user_id):
  tags_record = list(filter(lambda k: k[1][0] >= 2 and k[1][1] - k[1][0] >= 1, tags_stat(user_id).items()))
  random.shuffle(tags_record)
  return select_with_tags(user_id, tags_record)


@get_problems_entity_list_helper
@use_cached_result
def unfamiliar_problems(user_id):
  tags_record = list(filter(lambda k: k[1][0] < 2 and k[1][1] - k[1][0] >= 1, tags_stat(user_id).items()))
  random.shuffle(tags_record)
  return select_with_tags(user_id, tags_record)
