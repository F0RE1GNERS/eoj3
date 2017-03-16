from django.conf.urls import url

from .views import ContestList, dashboard

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', dashboard, name='dashboard'),
]