from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, ContestStandings, ContestSubmit, DashboardView
from .views import ContestMySubmission, ContestStatus

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<cid>\d+)/$', DashboardView.as_view(), name='dashboard'),
    url(r'^(?P<cid>\d+)/standings/$', ContestStandings.as_view(), name='standings'),
    url(r'^(?P<cid>\d+)/problem/(?P<pid>\w+)/$', ContestProblemDetail.as_view(), name='problem'),
    url(r'^(?P<cid>\d+)/submit/$', ContestSubmit.as_view(), name='submit'),
    url(r'^(?P<cid>\d+)/submission/$', ContestMySubmission.as_view(), name='submission'),
    url(r'^(?P<cid>\d+)/status/$', ContestStatus.as_view(), name='status'),
]