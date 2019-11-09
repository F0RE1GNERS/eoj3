from rest_framework.authentication import SessionAuthentication


class UnsafeSessionAuthentication(SessionAuthentication):
  def enforce_csrf(self, request):
    return
