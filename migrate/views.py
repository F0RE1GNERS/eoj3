from django.db import transaction
from .models import OldUser, OldSubmission, OldDiscussion
from submission.models import Submission, SubmissionStatus
from problem.models import Problem
from blog.models import Comment
import threading
from hashlib import sha1


def verify_old_user(user, pwd):
    return OldUser.objects.filter(username=user, password='*' + sha1(sha1(pwd.encode()).digest()).hexdigest().upper()).exists()


class MigrationThread(threading.Thread):

    def __init__(self, username, request_user):
        super().__init__()
        self.username = username
        self.new_user = str(request_user.pk)

    def run(self):
        with transaction.atomic():
            for submission in OldSubmission.objects.filter(author=self.username).all():
                Submission.objects.create(lang=submission.lang,
                                          code=submission.code,
                                          problem_id=str(submission.problem),
                                          author_id=self.new_user,
                                          create_time=submission.create_time,
                                          judge_start_time=submission.judge_start_time,
                                          judge_end_time=submission.judge_start_time,
                                          status=submission.status,
                                          status_percent=submission.status_percent,
                                          status_detail=submission.status_detail,
                                          status_time=submission.status_time,
                                          status_memory=submission.status_memory,
                                          code_length=len(submission.code))
                problem = Problem.objects.select_for_update().get(pk=str(submission.problem))
                problem.add_submit()
                if submission.status == SubmissionStatus.ACCEPTED:
                    problem.add_accept()
                problem.save(update_fields=["total_submit_number", "total_accept_number"])
            OldSubmission.objects.filter(author=self.username).all().delete()

            for comment in OldDiscussion.objects.filter(author=self.username).all():
                Comment.objects.create(text=comment.text,
                                       author_id=self.new_user,
                                       create_time=comment.create_time,
                                       problem_id=str(comment.problem))
            OldDiscussion.objects.filter(author=self.username).all().delete()

