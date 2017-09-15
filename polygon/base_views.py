import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import HttpResponse


def response_ok(**kwargs):
    kwargs.update(status='received')
    return HttpResponse(json.dumps(kwargs))


class PolygonBaseMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.polygon_enabled
