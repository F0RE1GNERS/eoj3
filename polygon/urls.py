from django.conf.urls import url

from .views import (
    home_view, register_view, SessionList, SessionCreate, SessionPull,
    ProblemAccess, SessionEdit, SessionSaveMeta, SessionEditUpdateAPI,
    SessionCreateStatement, SessionDeleteStatement, SessionGetStatementRaw, SessionUpdateStatement,
    SessionUpdateStatementRole, SessionUploadRegularFile, SessionDeleteRegularFile
)


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
    url(r'^session/$', SessionList.as_view(), name='session'),
    url(r'^session/create/$', SessionCreate.as_view(), name='session_create'),
    url(r'^session/pull/$', SessionPull.as_view(), name='session_pull'),
    url(r'^problem/(?P<pk>\d+)/access/$', ProblemAccess.as_view(), name='problem_access'),
    url(r'^session/(?P<sid>\d+)/edit/$', SessionEdit.as_view(), name='session_edit'),

    url(r'^session/(?P<sid>\d+)/meta/save/$', SessionSaveMeta.as_view(), name='session_save_meta'),

    url(r'^session/(?P<sid>\d+)/statement/add/$', SessionCreateStatement.as_view(), name='session_create_statement'),
    url(r'^session/(?P<sid>\d+)/statement/delete/$', SessionDeleteStatement.as_view(), name='session_delete_statement'),
    url(r'^session/(?P<sid>\d+)/statement/get/$', SessionGetStatementRaw.as_view(), name='session_get_statement_raw'),
    url(r'^session/(?P<sid>\d+)/statement/update/role/$', SessionUpdateStatementRole.as_view(),
        name='session_update_statement_role'),
    url(r'^session/(?P<sid>\d+)/statement/update/$', SessionUpdateStatement.as_view(), name='session_update_statement'),

    url(r'^session/(?P<sid>\d+)/files/add/$', SessionUploadRegularFile.as_view(), name='session_upload_regular_file'),
    url(r'^session/(?P<sid>\d+)/files/delete/$', SessionDeleteRegularFile.as_view(), name='session_delete_regular_file'),

    url(r'^session/(?P<sid>\d+)/api/$', SessionEditUpdateAPI.as_view(), name='session_update_api'),
]