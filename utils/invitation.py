from .models import InvitationCode


def generate(group, number, comment):
    for _ in range(int(number)):
        InvitationCode.objects.create(group_id=group.id, comment=comment)