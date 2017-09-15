from django.conf.urls import url, include

import polygon.views as v

urlpatterns = [
    url(r'^$', v.home_view, name='home'),
    url(r'^register/$', v.register_view, name='register'),
    url(r'^rejudge/problem/(?P<pk>\d+)/$', v.RejudgeProblem.as_view(), name='rejudge_problem'),
    url(r'^rejudge/(?P<sid>\d+)/$', v.RejudgeSubmission.as_view(), name='rejudge_submission'),
    url(r'^problem/', include('polygon.problem.urls')),
    url(r'^runs/$', v.RunsList.as_view(), name='runs'),
    url(r'^runs/message/(?P<pk>\d+)/$', v.RunMessageView.as_view(), name='run_message'),
    url(r'^contest/', include('polygon.contest.urls'))
]
