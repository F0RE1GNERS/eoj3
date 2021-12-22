from threading import Thread

from django.db import transaction

from problem.tasks import judge_submission_on_problem
from submission.models import Submission
from submission.util import SubmissionStatus
from .models import Contest, ContestParticipant
from .statistics import invalidate_contest, invalidate_contest_participant, invalidate_contest_problem


def judge_submission_on_contest(submission: Submission, callback=None, **kwargs):
  def _callback():
    invalidate_contest_participant(contest, submission.author_id)
    invalidate_contest_problem(contest, submission.problem_id)
    if callback:
      callback()

  contest = submission.contest or kwargs.get('contest')
  sync = kwargs.get('sync', False)
  if contest is None:
    raise ValueError('Judge on "None" contest')
  cases = 'all' if contest.system_tested else contest.run_tests_during_contest
  run_until_complete = contest.scoring_method == 'oi' and not submission.problem.group_enabled
  if not submission.contest:
    cases = 'all'
    _callback = None

  if cases != 'none':
    judge_submission_on_problem(submission, callback=_callback, case=cases,
                                run_until_complete=run_until_complete,
                                status_for_pretest=cases != 'all', sync=sync)
  else:
    submission.status = SubmissionStatus.SUBMITTED
    submission.save(update_fields=['status'])
    Thread(target=_callback).start()


def add_participant_with_invitation(contest_pk, invitation_pk, user):
  with transaction.atomic():
    contest = Contest.objects.get(pk=contest_pk)
    invitation = contest.contestinvitation_set.get(pk=invitation_pk)
    if contest.contestparticipant_set.filter(user=user).exists():
      participant = contest.contestparticipant_set.get(user=user)
      participant.comment = invitation.comment
      participant.save(update_fields=['comment'])
    else:
      ContestParticipant.objects.create(user=user, comment=invitation.comment, contest=contest)
    if invitation.availability == 1:
      invitation.delete()
    else:
      invitation.availability -= 1
      invitation.save(update_fields=['availability'])
  invalidate_contest(contest)
