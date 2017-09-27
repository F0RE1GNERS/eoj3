from django.contrib.auth import get_user_model

from account.models import Privilege
from django.contrib.auth.backends import ModelBackend


def is_admin_or_root(user):
    return user.is_authenticated and user.privilege in (Privilege.ROOT, Privilege.ADMIN)


def is_volunteer(user):
    return user.is_authenticated and user.privilege == Privilege.VOLUNTEER


class UsernameOrEmailModelBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}
        try:
            user = UserModel.objects.get(**kwargs)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
