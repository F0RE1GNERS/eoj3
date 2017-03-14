from django.db import models
from group.models import Group
import shortuuid


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


class InvitationCode(models.Model):
    code = models.CharField(max_length=32, default=get_invitation_code, unique=True, primary_key=True)
    group_id = models.IntegerField()
    create_time = models.DateTimeField(auto_now_add=True)
