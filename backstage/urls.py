from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^problem/$', problem, name='problem'),
    url(r'^problem/create', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/edit/(?P<pk>\d+)/', ProblemUpdate.as_view(), name='problem_edit')
]