from django.conf.urls import url

from backstage.problem.views import index, problem_home, group_edit
from backstage.problem.views import ProblemCreate, ProblemUpdate, ProblemList

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^problem/create', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/edit/(?P<pk>\d+)/', ProblemUpdate.as_view(), name='problem_edit'),
    url(r'^problem/$', problem_home, name='problem'),
    url(r'^problem/(?P<page>\d+)$', ProblemList.as_view(), name='problem_list'),
    url(r'^group/', group_edit, name='group')
]