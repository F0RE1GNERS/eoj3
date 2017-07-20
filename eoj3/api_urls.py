from django.conf import settings
from django.conf.urls import url

from submission.views import submission_count_api
from utils.markdown3 import markdown_convert_api

urlpatterns = [
    url(r'submission/user/(?P<name>.*)', submission_count_api),
    url(r'markdown/$', markdown_convert_api)
]


if settings.DEBUG:
    from account.api_views import RegisterAPI, LoginAPI
    from contest.api_views import ContestSubmitAPI
    urlpatterns += [
        url(r'^register', RegisterAPI.as_view()),
        url(r'^login', LoginAPI.as_view()),
        url(r'^contest/submit', ContestSubmitAPI.as_view())
    ]


