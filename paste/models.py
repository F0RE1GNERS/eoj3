from django.db import models

from account.models import User
from utils.language import LANG_CHOICE


class Paste(models.Model):
    fingerprint = models.CharField(unique=True, max_length=64)
    code = models.TextField(blank=False)
    lang = models.CharField(default='cpp', max_length=12, choices=LANG_CHOICE)
    created_by = models.ForeignKey(User, related_name="created_pastes", on_delete=models.CASCADE)
    public_access = models.PositiveIntegerField(choices=(
        (0, 'Only to yourself'),
        (10, 'Only to invited'),
        (20, 'Open to everyone')
    ), default=20)
    create_time = models.DateTimeField(auto_now_add=True)
    invited_users = models.ManyToManyField(User, related_name="invited_pastes")
    is_deleted = models.BooleanField(default=False)
    expire_after = models.IntegerField(choices=(
        (-1, 'Never'),
        (1, '1 minute'),
        (10, '10 minutes'),
        (60, '1 hour'),
        (300, '5 hours'),
        (1440, '1 day'),
        (43200, '30 days'),
    ), default=-1)
