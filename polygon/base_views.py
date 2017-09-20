from django.contrib.auth.mixins import UserPassesTestMixin


class PolygonBaseMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.polygon_enabled
