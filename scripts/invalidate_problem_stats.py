import progressbar

from problem.statistics import invalidate_problem
from problem.models import Problem

def run(*args):
  for problem in progressbar.progressbar(Problem.objects.all()):
    invalidate_problem(problem)
