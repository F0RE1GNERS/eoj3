from problem.views import StatusList
from contest.base import BaseContestMixin

class ContestDebug(BaseContestMixin, StatusList):
  template_name = 'contest/debug.jinja2'
  privileged = True

