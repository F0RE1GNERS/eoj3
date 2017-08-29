from django.conf.urls import url

import problem.views as v


urlpatterns = [
    url(r'^$', v.ProblemList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', v.ProblemView.as_view(), name='detail'),
    url(r'^(?P<pk>\d+)/submit/$', v.ProblemSubmitView.as_view(), name='submit'),
    url(r'^(?P<pk>\d+)/discussion/$', v.DiscussionView.as_view(), name='discussion'),
    url(r'^(?P<pk>\d+)/submission/(?P<sid>\d+)/api/$', v.ProblemPersonalSubmissionAPI.as_view(), name='submission_api'),
    url(r'^(?P<pk>\d+)/submission/(?P<sid>\d+)/$', v.ProblemSubmissionView.as_view(), name='submission'),
    url(r'^(?P<pk>\d+)/submission/(?P<sid>\d+)/$', v.ProblemSubmissionView.as_view(), name='rejudge_submission'),
    url(r'^(?P<pk>\d+)/submission/past/$', v.ProblemPersonalOlderSubmissionsAPI.as_view(), name='past_submission'),
    url(r'^status/$', v.StatusList.as_view(), name='status'),
    url(r'^millionaire/$', v.Millionaires.as_view(), name='millionaire'),
    url(r'^(?P<pk>\d+)/statistics/$', v.ProblemStatisticsView.as_view(), name='statistics'),
]