from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db import transaction

from .models import Payment, User


def create_payment(user: User, credit, type, memo):
    user.refresh_from_db(fields=["score"])
    user.score += credit
    if user.score < 0:
        raise PermissionDenied("You are running out of EMB...")
    user.save(update_fields=["score"])
    payment = Payment.objects.create(user=user, type=type, credit=credit, balance=user.score)
    payment.detail = memo
    payment.save(update_fields=["detail_message"])


def transfer(user1, user2, amount):
    """from user1 to user2"""
    with transaction.atomic():
        create_payment(user1, -amount, Payment.TRANSFER, {"to": user2.pk})
        create_payment(user2, amount, Payment.TRANSFER, {"from": user2.pk})


def reward_problem_ac(user, amount, problem_id):
    with transaction.atomic():
        create_payment(user, amount, Payment.REWARD, {"type": "problem", "id": problem_id})


def change_username(user, amount, new_username):
    with transaction.atomic():
        try:
            user.username = new_username
            if len(new_username) < 6 or '#' in new_username:
                raise PermissionDenied("Username too short or illegal.")
            user.save(update_fields=["username"])
        except IntegrityError:
            raise PermissionDenied("Username should be unique.")
        create_payment(user, amount, Payment.CHANGE_USERNAME, {"new": new_username})


def download_case(user, amount, memo):
    with transaction.atomic():
        create_payment(user, amount, Payment.DOWNLOAD_CASE, memo)
