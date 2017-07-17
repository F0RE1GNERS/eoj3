from django.conf.urls import url

from .views import home_view, register_view


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
]