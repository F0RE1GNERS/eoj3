from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, ContestStandings, ContestSubmit, DashboardView
from .views import ContestMySubmission, ContestStatus, ContestBoundUser, ContestUpdateStandings
from .views import ContestClarificationView, ContestClarificationToggle, ContestClarificationQuery

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<cid>\d+)/$', DashboardView.as_view(), name='dashboard'),
    url(r'^(?P<cid>\d+)/standings/$', ContestStandings.as_view(), name='standings'),
    url(r'^(?P<cid>\d+)/problem/(?P<pid>\w+)/$', ContestProblemDetail.as_view(), name='problem'),
    url(r'^(?P<cid>\d+)/submit/$', ContestSubmit.as_view(), name='submit'),
    url(r'^(?P<cid>\d+)/submission/$', ContestMySubmission.as_view(), name='submission'),
    url(r'^(?P<cid>\d+)/status/$', ContestStatus.as_view(), name='status'),
    url(r'^(?P<cid>\d+)/clarification/$', ContestClarificationView.as_view(), name='clarification'),
    url(r'^(?P<cid>\d+)/clarification/(?P<clarification_id>\d+)/(?P<operation>\w+)/$', ContestClarificationToggle.as_view(), name='clarification_toggle'),
    url(r'^(?P<cid>\d+)/clarification/update/$', ContestClarificationQuery.as_view(), name='clarification_update'),
    url(r'^(?P<cid>\d+)/invitation/$', ContestBoundUser.as_view(), name='invitation'),
    url(r'^(?P<cid>\d+)/update_standings/$', ContestUpdateStandings.as_view(), name='update_standings'),
]