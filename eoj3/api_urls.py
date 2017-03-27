from django.conf.urls import url
from django.conf import settings

from account.api_views import RegisterAPI, LoginAPI
from contest.api_views import ContestSubmitAPI

urlpatterns = []



if settings.DEBUG:
    urlpatterns += [
        url(r'^register', RegisterAPI.as_view()),
        url(r'^login', LoginAPI.as_view()),
        url(r'^contest/submit', ContestSubmitAPI.as_view())
    ]


