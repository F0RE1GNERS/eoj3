from django.conf import settings
from django.conf.urls import url

from home import search_api
from submission.views import submission_count_api
from utils.markdown3 import markdown_convert_api
from polygon.views import RunStatus
from message.views import ReplyAPI, ConversationAPI

urlpatterns = [
    url(r'^submission/user/(?P<name>.*)/$', submission_count_api),
    url(r'^markdown/$', markdown_convert_api),
    url(r'^search/$', search_api.SearchAPI.as_view(), name='search'),
    url(r'^search/user/$', search_api.SearchUserAPI.as_view(), name='user_search'),
    url(r'^search/problem/$', search_api.SearchProblemAPI.as_view(), name='problem_search'),
    url(r'^polygon/run/(?P<pk>\d+)/$', RunStatus.as_view()),
    url(r'^message/reply/(?P<pk>\d+)/$', ReplyAPI.as_view()),
    url(r'^message/c/(?P<pk>\d+)/$', ConversationAPI.as_view()),
]


if settings.DEBUG:
    from home.api_views import RegisterAPI, LoginAPI
    from contest.api_views import ContestSubmitAPI
    urlpatterns += [
        url(r'^register', RegisterAPI.as_view()),
        url(r'^login', LoginAPI.as_view()),
        url(r'^contest/submit', ContestSubmitAPI.as_view())
    ]


