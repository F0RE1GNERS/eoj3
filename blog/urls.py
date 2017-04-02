from django.conf.urls import url
from . import views

urlpatterns = [
    url('^create/$', views.BlogCreate.as_view(), name='create'),
    url('^entry/(?P<pk>\d+)/$', views.BlogView.as_view(), name='detail')
]
