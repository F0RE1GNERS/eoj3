import progressbar

from problem.models import Problem
from problem.statistics import invalidate_problem


def run(*args):
  for problem in progressbar.progressbar(Problem.objects.all()):
    invalidate_problem(problem)
