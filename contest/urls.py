from django.conf.urls import url

from .views import ContestList, dashboard, standings

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^(?P<pk>\d+)/$', dashboard, name='dashboard'),
    url(r'^(?P<pk>\d+)/standings/$', standings, name='standings'),
]