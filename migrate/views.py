import threading
from hashlib import sha1

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django_comments_xtd.models import XtdComment

from account.models import User
from problem.models import Problem
from problem.statistics import get_problem_difficulty
from submission.models import Submission, SubmissionStatus
from .models import OldUser, OldSubmission, OldDiscussion

problem_content_type = ContentType.objects.get_for_model(Problem)


def verify_old_user(user, pwd):
    return OldUser.objects.filter(username=user,
                                  password='*' + sha1(sha1(pwd.encode()).digest()).hexdigest().upper()).exists()


class MigrationThread(threading.Thread):
    def __init__(self, username, request_user):
        super().__init__()
        self.username = username
        self.new_user = str(request_user.pk)

    def run(self):
        with transaction.atomic():
            for submission in OldSubmission.objects.filter(author=self.username).order_by("create_time").all():
                s = Submission.objects.create(lang=submission.lang,
                                              code=submission.code,
                                              problem_id=str(submission.problem),
                                              author_id=self.new_user,
                                              judge_end_time=submission.judge_start_time,
                                              status=submission.status,
                                              status_private=submission.status,
                                              status_percent=submission.status_percent,
                                              status_detail=submission.status_detail,
                                              status_time=submission.status_time / 1000)
                s.create_time = submission.create_time
                s.save(update_fields=["create_time"])
                if Submission.objects.filter(author_id=s.author_id, problem_id=s.problem_id, contest__isnull=True,
                                             status=SubmissionStatus.ACCEPTED).last() == s:
                    with transaction.atomic():
                        author = User.objects.select_for_update().get(pk=self.new_user)
                        author.score += get_problem_difficulty(submission.problem)
                        author.save(update_fields=['score'])
            OldSubmission.objects.filter(author=self.username).all().delete()

            for c in OldDiscussion.objects.filter(author=self.username).order_by("create_time"):
                XtdComment.objects.create(
                    user=self.new_user,
                    submit_date=c.create_time,
                    object_pk=c.problem,
                    comment=c.text,
                    content_type=problem_content_type,
                    site_id=1
                )
            OldDiscussion.objects.filter(author=self.username).all().delete()
