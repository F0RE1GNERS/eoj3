from django.conf.urls import url
from . import views

urlpatterns = [
    url('^create/$', views.BlogCreate.as_view(), name='create'),
]
