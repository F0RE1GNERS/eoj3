from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, standings, ContestSubmit, BaseContestView

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', BaseContestView.as_view(), name='dashboard'),
    url(r'^(?P<pk>\d+)/standings/$', standings, name='standings'),
    url(r'^(?P<pk>\d+)/problem/(?P<pid>\w+)/$', ContestProblemDetail.as_view(), name='problem'),
    url(r'^(?P<pk>\d+)/submit/$', ContestSubmit.as_view(), name='submit'),
]