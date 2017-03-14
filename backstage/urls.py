from django.conf.urls import url

from backstage.problem.views import index, ProblemCreate, ProblemUpdate, ProblemList

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^problem/create', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/edit/(?P<pk>\d+)/', ProblemUpdate.as_view(), name='problem_edit'),
    url(r'^problem/(?P<page>\d+)$', ProblemList.as_view(), name='problem'),
]