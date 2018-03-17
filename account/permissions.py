from django.contrib.auth import get_user_model

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.mixins import AccessMixin


def is_admin_or_root(user):
    return user.is_authenticated and user.is_staff


def is_volunteer(user):
    return False


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


class StaffRequiredMixin(AccessMixin):
    """
    CBV mixin which verifies that the current user is staff.
    """
    def dispatch(self, request, *args, **kwargs):
        if not is_admin_or_root(request.user):
            return self.handle_no_permission()
        return super(StaffRequiredMixin, self).dispatch(request, *args, **kwargs)
