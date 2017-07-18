from django.conf.urls import url

from .views import home_view, register_view, SessionList, session_create


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
    url(r'^session/$', SessionList.as_view(), name='session'),
    url(r'^session/create/$', session_create, name='session_create'),

]