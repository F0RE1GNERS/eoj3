from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.views.generic import ListView
from django.utils.translation import ugettext_lazy as _

from .models import Payment, User, UsernameValidator


def create_payment(user: User, credit, type, memo):
    user.refresh_from_db(fields=["score"])
    user.score += credit
    if user.score < 0:
        raise PermissionDenied(_("You are running out of EMB..."))
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


def reward_contest_ac(user, amount, contest_id):
    with transaction.atomic():
        create_payment(user, amount, Payment.REWARD, {"type": "contest", "id": contest_id})


def change_username(user, amount, new_username):
    with transaction.atomic():
        try:
            user.username = User.normalize_username(new_username)
            UsernameValidator()(user.username)
            user.save(update_fields=["username"])
        except ValidationError:
            raise PermissionDenied(_("Username too short or illegal."))
        except IntegrityError:
            raise PermissionDenied(_("Username should be unique."))
        create_payment(user, amount, Payment.CHANGE_USERNAME, {"new": new_username})


def download_case(user, amount, memo):
    with transaction.atomic():
        create_payment(user, amount, Payment.DOWNLOAD_CASE, memo)


class PaymentList(LoginRequiredMixin, ListView):
    paginate_by = 20
    template_name = 'account/payment_list.jinja2'
    context_object_name = 'payment_list'

    def get_queryset(self):
        return self.request.user.payment_set.all()
