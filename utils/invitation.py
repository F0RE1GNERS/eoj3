from django.core.exceptions import ValidationError

from .models import InvitationCode
from group.models import GroupMembership, Group


def generate(group, number, comment):
    for _ in range(int(number)):
        InvitationCode.objects.create(group_id=group.id, comment=comment)


def activate(user, code):
    invitation = InvitationCode.objects.filter(code=code).first()
    if not invitation:
        return None, "Invitation code is invalid."
    group = Group.objects.get(pk=invitation.group_id)
    membership = GroupMembership(group=group, user=user, comment=invitation.comment)
    try:
        membership.full_clean()
    except ValidationError:
        return None, "You cannot join a group twice."
    membership.save()
    invitation.delete()
    return membership, ''
