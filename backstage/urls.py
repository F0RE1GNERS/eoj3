from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^problem/$', problem, name='problem'),
    url(r'^problem/add', problem_add, name='problem_add'),
]