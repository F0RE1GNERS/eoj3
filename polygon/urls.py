from django.conf.urls import url

from .views import home_view, register_view, SessionList, session_create, session_pull


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
    url(r'^session/$', SessionList.as_view(), name='session'),
    url(r'^session/create/$', session_create, name='session_create'),
    url(r'^session/pull/$', session_pull, name='session_pull'),

]