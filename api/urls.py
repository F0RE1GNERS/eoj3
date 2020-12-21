from django.conf.urls import url
from rest_framework_simplejwt.views import (
  TokenObtainPairView,
  TokenRefreshView,
  TokenVerifyView
)

from api.views import tag
from api.views.problem import ProblemView
from api.views.problemlist import ProblemListView
from api.views.user import UserView
from home import search_api
from submission.views import submission_code_api, submission_count_api
from utils.markdown3 import markdown_convert_api
from utils.site_settings import force_closed
from .views.submission import SubmissionListView

app_name = "api"

urlpatterns = [
  url(r'^submission/$', submission_code_api, kwargs=force_closed()),  # TODO: need test
  url(r'^submission/user/(?P<name>.*)/$', submission_count_api),
  url(r'^markdown/$', markdown_convert_api),
  url(r'^search/$', search_api.SearchAPI.as_view(), name='search', kwargs=force_closed()),
  url(r'^search/user/$', search_api.SearchUserAPI.as_view(), name='user_search', kwargs=force_closed()),
  url(r'^search/problem/$', search_api.SearchProblemAPI.as_view(), name='problem_search', kwargs=force_closed()),
]

urlpatterns += [
  url(r'^token/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
  url(r'^token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
  url(r'^token/verify/$', TokenVerifyView.as_view(), name='token_verify'),
]

urlpatterns += [  # TODO: for App only?
  url(r'^status/hidden/$', SubmissionListView.as_view(), kwargs=force_closed()),
  url(r'^problem/(?P<pk>\d+)/$', ProblemView.as_view(), kwargs=force_closed()),
  url(r'^user/(?P<pk>\d+)/$', UserView.as_view(), kwargs=force_closed()),
  url(r'^problem_list/(?P<pk>\d+)/$', ProblemListView.as_view(), kwargs=force_closed()),
  url(r'^tag/$', tag.return_problems, kwargs=force_closed())
]
