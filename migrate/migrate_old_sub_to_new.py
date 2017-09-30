import random
import traceback

from django.db import transaction

from account.models import MAGIC_CHOICE
from account.models import User
from migrate.models import OldSubmission
from submission.models import Submission
from utils import random_string
from utils.identicon import Identicon


def run():
    try:
        with transaction.atomic():
            idx = 0
            for submission in OldSubmission.objects.order_by("create_time").all():
                if idx % 1000 == 0:
                    print(idx)
                username = submission.author
                username_registered = username + '#old'
                if not User.objects.filter(username=username_registered).exists():
                    email = username + '@acm.cs.ecnu.edu.cn'
                    user = User.objects.create(username=username_registered, email=email,
                                               magic=random.choice(list(dict(MAGIC_CHOICE).keys())))
                    user.set_password(random_string())
                    user.save()
                    user.avatar.save('generated.png', Identicon(user.email).get_bytes())
                else:
                    user = User.objects.get(username=username_registered)
                s = Submission.objects.create(lang=submission.lang,
                                              code=submission.code,
                                              problem_id=str(submission.problem),
                                              author=user,
                                              judge_end_time=submission.judge_start_time,
                                              status=submission.status,
                                              status_private=submission.status,
                                              status_percent=submission.status_percent,
                                              status_detail=submission.status_detail,
                                              status_time=submission.status_time / 1000)
                s.create_time = submission.create_time
                s.save(update_fields=["create_time"])
                idx += 1
            OldSubmission.objects.all().delete()
    except:
        traceback.print_exc()