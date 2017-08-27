from account.models import User
from submission.statistics import get_accept_problem_list
from problem.statistics import get_many_problem_difficulty

def run():
    for user in User.objects.all():
        user.score = sum(get_many_problem_difficulty(get_accept_problem_list(user.pk)).values())
        if user.score > 0:
            print(user.score)
            user.save(update_fields=['score'])
