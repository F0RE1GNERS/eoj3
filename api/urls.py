from django.conf.urls import url
from rest_framework_simplejwt.views import (
  TokenObtainPairView,
  TokenRefreshView,
  TokenVerifyView
)

from api.views.problem import ProblemView
from home import search_api
from submission.views import submission_code_api, submission_count_api
from utils.markdown3 import markdown_convert_api

from .views.submission import SubmissionListView

app_name = "api"

urlpatterns = [
  url(r'^submission/$', submission_code_api),
  url(r'^submission/user/(?P<name>.*)/$', submission_count_api),
  url(r'^markdown/$', markdown_convert_api),
  url(r'^search/$', search_api.SearchAPI.as_view(), name='search'),
  url(r'^search/user/$', search_api.SearchUserAPI.as_view(), name='user_search'),
  url(r'^search/problem/$', search_api.SearchProblemAPI.as_view(), name='problem_search'),
]

urlpatterns += [
  url(r'^token/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  url(r'^token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
  url(r'^token/verify/$', TokenVerifyView.as_view(), name='token_verify'),
]

urlpatterns += [
  url(r'^status/hidden/$', SubmissionListView.as_view()),
  url(r'^problem/(?P<pk>\d+)/$', ProblemView.as_view()),
]
