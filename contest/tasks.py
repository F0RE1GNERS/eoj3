from django.utils import timezone
from django.db import transaction
from .models import Contest, ContestParticipant
from account.models import User
from problem.tasks import judge_submission_on_problem
from submission.models import SubmissionStatus, Submission
from .statistics import invalidate_contest, invalidate_contest_participant
from threading import Thread


def judge_submission_on_contest(submission: Submission, callback=None, **kwargs):

    def _callback():
        invalidate_contest_participant(contest, submission.author_id)
        if callback:
            callback()

    contest = submission.contest or kwargs.get('contest')
    cases = 'all' if contest.status > 0 else contest.run_tests_during_contest
    run_until_complete = contest.scoring_method == 'oi'
    if not submission.contest:
        cases = 'all'
        _callback = None

    if cases != 'none':
        judge_submission_on_problem(submission, callback=_callback, case=cases,
                                    status_private=contest.is_frozen, run_until_complete=run_until_complete,
                                    status_for_pretest=cases != 'all')
    else:
        submission.status = submission.status_private = SubmissionStatus.SUBMITTED
        submission.save(update_fields=['status', 'status_private'])
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
        invitation.delete()
    invalidate_contest(contest)
