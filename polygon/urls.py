from django.conf.urls import url

from .views import (
    home_view, register_view, SessionList, SessionCreate, SessionPull,
    ProblemAccess, SessionEdit, SessionSaveMeta
)


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
    url(r'^session/$', SessionList.as_view(), name='session'),
    url(r'^session/create/$', SessionCreate.as_view(), name='session_create'),
    url(r'^session/pull/$', SessionPull.as_view(), name='session_pull'),
    url(r'^problem/(?P<pk>\d+)/access/$', ProblemAccess.as_view(), name='problem_access'),
    url(r'^session/(?P<sid>\d+)/edit/$', SessionEdit.as_view(), name='session_edit'),
    url(r'^session/(?P<sid>\d+)/save/meta/$', SessionSaveMeta.as_view(), name='session_save_meta'),
]