from rest_framework.authentication import SessionAuthentication
from account.permissions import is_admin_or_root
from .models import SiteSettings


class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


def test_site_open(request):
    if is_admin_or_root(request.user):
        return True
    if not SiteSettings.objects.exists():
        SiteSettings.objects.create()
    return SiteSettings.objects.first().open
