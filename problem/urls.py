from django.conf.urls import url

from .views import ProblemList, ProblemView, StatusList, ProblemSubmitView


urlpatterns = [
    url(r'^$', ProblemList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', ProblemView.as_view(), name='detail'),
    url(r'^(?P<pk>\d+)/submit/$', ProblemSubmitView.as_view(), name='submit'),
    url(r'^status/$', StatusList.as_view(), name='status'),
]