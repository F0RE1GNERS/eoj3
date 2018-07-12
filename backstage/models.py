from django.db import models

from account.models import User


class Email(models.Model):
    title = models.CharField(max_length=192)
    content = models.TextField(blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, null=True, related_name="sent_emails", on_delete=models.SET_NULL)


class UpdateLog(models.Model):
    create_time = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=10, choices=(
        ('fix', 'BUG FIX'),
        ('add', 'NEW FEATURE'),
        ('del', 'REMOVE FEATURE'),
        ('ref', 'REFACTOR'),
        ('upd', 'UPDATE'),
        ('enhance', 'ENHANCEMENT'),
    ))
    priority = models.PositiveIntegerField(choices=(
        (0, 'CRITICAL'),
        (1, 'HIGH'),
        (2, 'MEDIUM'),
        (3, 'LOW'),
    ))
    is_about_polygon = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    content = models.TextField()
