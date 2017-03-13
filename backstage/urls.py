from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^problem/$', problem, name='problem'),
    url(r'^problem/add', problem_add, name='problem_add'),
    url(r'^problem/edit/(?P<problem_pk>\d+)/', problem_edit, name='problem_edit')
]