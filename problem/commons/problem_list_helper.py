import functools

from django.contrib.contenttypes.models import ContentType
from tagging.models import TaggedItem

from problem.models import Problem
from problem.statistics import get_attempted_problem_list, get_accept_problem_list


def attach_personal_solve_info(problems, user_id):
  attempt_list = set(get_attempted_problem_list(user_id))
  accept_list = set(get_accept_problem_list(user_id))
  for problem in problems:
    problem.personal_label = 0
    if problem.id in accept_list:
      problem.personal_label = 1
    elif problem.id in attempt_list:
      problem.personal_label = -1


def attach_tag_info(problems):
  tagged_items = list(TaggedItem.objects.filter(content_type=ContentType.objects.get_for_model(Problem))
                      .filter(object_id__in=[problem.pk for problem in problems]).select_related("tag"))
  for problem in problems:
    items = [x for x in tagged_items if x.object_id == problem.pk]
    if items:
      problem.my_tags = list(map(lambda x: x.tag.name, items))


def get_problems_entity_list_helper(func):
  @functools.wraps(func)
  def wrapper(user_id):
    problem_id_list = func(user_id)
    if isinstance(problem_id_list, list):
      orders = {problem_id: k for k, problem_id in enumerate(problem_id_list)}
    problems = list(Problem.objects.filter(pk__in=problem_id_list))
    if isinstance(problem_id_list, list):
      problems.sort(key=lambda problem: orders.get(problem.id, 10 ** 9))
    attach_personal_solve_info(problems, user_id)
    attach_tag_info(problems)
    return problems

  return wrapper


def no_tags_entity_list_helper(func):
  @functools.wraps(func)
  def wrapper(user_id):
    problem_id_list = func(user_id)
    problems = list(Problem.objects.filter(pk__in=problem_id_list))
    attach_personal_solve_info(problems, user_id)
    return problems

  return wrapper
