from rest_framework.authentication import SessionAuthentication
from account.permissions import is_admin_or_root
from .models import get_site_settings


class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


def test_site_open(request):
    if is_admin_or_root(request.user):
        return True
    return get_site_settings().open
