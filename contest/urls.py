from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, ContestStandings, ContestSubmit, BaseContestView

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<cid>\d+)/$', BaseContestView.as_view(), name='dashboard'),
    url(r'^(?P<cid>\d+)/standings/$', ContestStandings.as_view(), name='standings'),
    url(r'^(?P<cid>\d+)/problem/(?P<pid>\w+)/$', ContestProblemDetail.as_view(), name='problem'),
    url(r'^(?P<cid>\d+)/submit/$', ContestSubmit.as_view(), name='submit'),
]