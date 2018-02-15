from django.conf.urls import url

from polygon.problem.views import base, asset, case, revision, statement


urlpatterns = [
    url(r'^$', base.ProblemList.as_view(), name='problem_list'),
    url(r'^create/$', base.ProblemCreate.as_view(), name='problem_create'),

    url(r'^(?P<pk>\d+)/revision/create/$', revision.RevisionCreateView.as_view(), name='revision_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/$', revision.RevisionUpdateView.as_view(), name='revision_view'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/fork/$', revision.RevisionForkView.as_view(), name='revision_fork'),
]
