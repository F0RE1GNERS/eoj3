from django.conf.urls import url

import problem.views as v


urlpatterns = [
    url(r'^$', v.ProblemList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', v.ProblemView.as_view(), name='detail'),
    url(r'^(?P<pk>\d+)/submit/$', v.ProblemSubmitView.as_view(), name='submit'),
    url(r'^(?P<pk>\d+)/submissions/$', v.ProblemPersonalSubmissionAPI.as_view(), name='submission'),
    url(r'^submission/(?P<pk>\d+)/$', v.ProblemSubmissionView.as_view(), name='submission_view'),
    url(r'^status/$', v.StatusList.as_view(), name='status'),
    url(r'^(?P<pk>\d+)/statistics/$', v.ProblemStatisticsView.as_view(), name='statistics'),
]