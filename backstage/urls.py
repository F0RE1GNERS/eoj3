from django.conf.urls import url

from .problem.views import index
from .problem.views import ProblemCreate, ProblemUpdate, ProblemList
from .group.views import GroupList, GroupUpdate, GroupCreate

urlpatterns = [
    url(r'^$', index, name='index'),

    url(r'^problem/$', ProblemList.as_view(), name='problem'),
    url(r'^problem/create', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/edit/(?P<pk>\d+)/', ProblemUpdate.as_view(), name='problem_edit'),

    url(r'^group/$', GroupList.as_view(), name='group'),
    url(r'^group/create/', GroupCreate.as_view(), name='group_create'),
    url(r'^group/edit/(?P<pk>\d+)/', GroupUpdate.as_view(), name='group_edit'),

]