from django.db import transaction

from account.models import User


def update_color():
    colors = [(.05, 'red'),
              (.15, 'orange'),
              (.30, 'purple'),
              (.50, 'blue'),
              (.75, 'teal'),
              (1., 'green')]
    with transaction.atomic():
        User.objects.all().update(magic='')
        User.objects.filter(is_staff=True).update(magic='grey')
        user_list = list(User.objects.filter(rating__gt=0, is_staff=False, is_superuser=False).order_by("-rating"))
        for idx, user in enumerate(user_list):
            if idx > 0 and user.rating == user_list[idx - 1].rating:
                user.magic = user_list[idx - 1].magic
            else:
                select_color = 0
                position = idx / len(user_list)
                while select_color < 5 and colors[select_color][0] < position:
                    select_color += 1
                user.magic = colors[select_color][1]
            print(user.username, user.magic)
            user.save(update_fields=['magic'])
