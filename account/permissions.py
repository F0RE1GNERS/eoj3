from django.contrib.auth import get_user_model

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.mixins import AccessMixin


def is_admin_or_root(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_coach(user):
    return user.is_authenticated and user.magic == "red"


class UsernameOrEmailModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            if '@' not in username:
                user = UserModel.objects.get(username=username)
            else:
                user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user


class StaffRequiredMixin(AccessMixin):
    """
    CBV mixin which verifies that the current user is staff.
    """
    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_root(request.user):
            return self.handle_no_permission()
        return super(StaffRequiredMixin, self).dispatch(request, *args, **kwargs)
