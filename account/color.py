from django.db import transaction

from account.models import User


def update_color():
    colors = [(1800, 'red'),
              (1700, 'orange'),
              (1600, 'purple'),
              (1500, 'blue'),
              (1350, 'teal'),
              (0, 'green')]
    with transaction.atomic():
        User.objects.all().update(magic='')
        User.objects.filter(is_superuser=True).update(magic='grey')
        User.objects.filter(is_staff=True).update(magic='grey')
        user_list = list(User.objects.filter(rating__gt=0, is_staff=False, is_superuser=False).order_by("-rating"))
        for idx, user in enumerate(user_list):
            select_color = 0
            while select_color < 5 and user.rating < colors[select_color][0]:
                select_color += 1
            user.magic = colors[select_color][1]
            # print(user.username, user.magic)
            user.save(update_fields=['magic'])
