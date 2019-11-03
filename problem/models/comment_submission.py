import django_comments
from django.db import models
from submission.models import Submission


class CommentSubmission(models.Model):
    comment = models.ForeignKey(django_comments.get_model(), on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
