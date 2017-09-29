from rest_framework.authentication import SessionAuthentication
from account.permissions import is_admin_or_root


class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return
