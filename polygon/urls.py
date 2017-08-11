from django.conf.urls import url

from .views import (
    home_view, register_view, SessionList, SessionCreate, SessionPull, SessionPush, SessionPullHotReload,
    ProblemMeta, ProblemPreview, ProblemStatus, SessionEdit, SessionSaveMeta, SessionEditUpdateAPI,
    SessionCreateStatement, SessionDeleteStatement, SessionGetStatementRaw, SessionUpdateStatement,
    SessionUploadRegularFile, SessionDeleteRegularFile, SessionUpdateProgram, SessionReadProgram,
    SessionCreateProgram, SessionDeleteProgram, SessionCreateCaseManually, SessionUpdateOrders,
    SessionPreviewCase, SessionImportProgram, SessionUploadCase, SessionReformCase, SessionUpdateCasePoint,
    SessionValidateCase, RunsList, RunMessageView, SessionRunCaseOutput, SessionCheckCaseOutput,
    SessionCheckAllCaseOutput, SessionRunAllCaseOutput, SessionValidateAllCase, SessionDeleteCase,
    SessionDownloadInput, SessionDownloadOutput, SessionGenerateInput, SessionAddCaseFromStress,
    SessionReformAllCase, SessionTogglePretestCase, SessionToggleSampleCase
)

from .contest import (
    ContestList, ContestEdit, ContestToggleVisible, ContestCreate, ContestAccessManage
)


urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'^register/$', register_view, name='register'),
    url(r'^session/$', SessionList.as_view(), name='session'),
    url(r'^session/create/$', SessionCreate.as_view(), name='session_create'),
    url(r'^session/pull/$', SessionPull.as_view(), name='session_pull'),
    url(r'^problem/(?P<pk>\d+)/preview/$', ProblemPreview.as_view(), name='problem_preview'),
    url(r'^problem/(?P<pk>\d+)/meta/$', ProblemMeta.as_view(), name='problem_meta'),
    url(r'^problem/(?P<pk>\d+)/status/$', ProblemStatus.as_view(), name='problem_status'),
    url(r'^runs/$', RunsList.as_view(), name='runs'),
    url(r'^runs/message/(?P<pk>\d+)/$', RunMessageView.as_view(), name='run_message'),
    url(r'^session/(?P<sid>\d+)/edit/$', SessionEdit.as_view(), name='session_edit'),
    url(r'^session/(?P<sid>\d+)/push/$', SessionPush.as_view(), name='session_push'),
    url(r'^session/(?P<sid>\d+)/pull/hot/$', SessionPullHotReload.as_view(), name='session_pull_hot'),

    url(r'^session/(?P<sid>\d+)/meta/save/$', SessionSaveMeta.as_view(), name='session_save_meta'),

    url(r'^session/(?P<sid>\d+)/statement/add/$', SessionCreateStatement.as_view(), name='session_create_statement'),
    url(r'^session/(?P<sid>\d+)/statement/delete/$', SessionDeleteStatement.as_view(), name='session_delete_statement'),
    url(r'^session/(?P<sid>\d+)/statement/get/$', SessionGetStatementRaw.as_view(), name='session_get_statement_raw'),
    url(r'^session/(?P<sid>\d+)/statement/update/$', SessionUpdateStatement.as_view(), name='session_update_statement'),

    url(r'^session/(?P<sid>\d+)/files/add/$', SessionUploadRegularFile.as_view(), name='session_upload_regular_file'),
    url(r'^session/(?P<sid>\d+)/files/delete/$', SessionDeleteRegularFile.as_view(), name='session_delete_regular_file'),

    url(r'^session/(?P<sid>\d+)/program/add/$', SessionCreateProgram.as_view(), name='session_create_program_file'),
    url(r'^session/(?P<sid>\d+)/program/update/$', SessionUpdateProgram.as_view(), name='session_update_program_file'),
    url(r'^session/(?P<sid>\d+)/program/delete/$', SessionDeleteProgram.as_view(), name='session_delete_program_file'),
    url(r'^session/(?P<sid>\d+)/program/read/$', SessionReadProgram.as_view(), name='session_read_program'),
    url(r'^session/(?P<sid>\d+)/program/import/$', SessionImportProgram.as_view(), name='session_import_program_file'),

    url(r'^session/(?P<sid>\d+)/case/add/$', SessionCreateCaseManually.as_view(), name='session_create_case_manually'),
    url(r'^session/(?P<sid>\d+)/case/order/$', SessionUpdateOrders.as_view(), name='session_update_orders'),
    url(r'^session/(?P<sid>\d+)/case/preview/$', SessionPreviewCase.as_view(), name='session_preview_case'),
    url(r'^session/(?P<sid>\d+)/case/upload/$', SessionUploadCase.as_view(), name='session_upload_case'),
    url(r'^session/(?P<sid>\d+)/case/reform/$', SessionReformCase.as_view(), name='session_reform_case'),
    url(r'^session/(?P<sid>\d+)/case/point/$', SessionUpdateCasePoint.as_view(), name='session_update_case_point'),
    url(r'^session/(?P<sid>\d+)/case/validate/$', SessionValidateCase.as_view(), name='session_validate_case'),
    url(r'^session/(?P<sid>\d+)/case/output/$', SessionRunCaseOutput.as_view(), name='session_run_case_with_model'),
    url(r'^session/(?P<sid>\d+)/case/check/$', SessionCheckCaseOutput.as_view(), name='session_check_case_output'),
    url(r'^session/(?P<sid>\d+)/case/reform/all/$', SessionReformAllCase.as_view(), name='session_reform_all_case'),
    url(r'^session/(?P<sid>\d+)/case/validate/all/$', SessionValidateAllCase.as_view(), name='session_validate_all_case'),
    url(r'^session/(?P<sid>\d+)/case/output/all/$', SessionRunAllCaseOutput.as_view(), name='session_run_all_case_with_model'),
    url(r'^session/(?P<sid>\d+)/case/check/all/$', SessionCheckAllCaseOutput.as_view(), name='session_check_all_case_output'),
    url(r'^session/(?P<sid>\d+)/case/delete/$', SessionDeleteCase.as_view(), name='session_delete_case'),
    url(r'^session/(?P<sid>\d+)/case/download/input/$', SessionDownloadInput.as_view(), name='session_download_case_input'),
    url(r'^session/(?P<sid>\d+)/case/download/output/$', SessionDownloadOutput.as_view(), name='session_download_case_output'),
    url(r'^session/(?P<sid>\d+)/case/generate/$', SessionGenerateInput.as_view(), name='session_generate_input'),
    url(r'^session/(?P<sid>\d+)/case/stress/$', SessionAddCaseFromStress.as_view(), name='session_create_case_from_stress'),
    url(r'^session/(?P<sid>\d+)/case/pretest/$', SessionTogglePretestCase.as_view(), name='session_toggle_pretest_case'),
    url(r'^session/(?P<sid>\d+)/case/sample/$', SessionToggleSampleCase.as_view(), name='session_toggle_sample_case'),

    url(r'^contest/list/$', ContestList.as_view(), name='contest_list'),
    url(r'^contest/create/$', ContestCreate.as_view(), name='contest_create'),
    url(r'^contest/(?P<pk>\d+)/visible/$', ContestToggleVisible.as_view(), name='contest_toggle_visible'),
    url(r'^contest/(?P<pk>\d+)/meta/$', ContestEdit.as_view(), name='contest_meta'),
    url(r'^contest/(?P<pk>\d+)/access/$', ContestAccessManage.as_view(), name='contest_access_manage'),

    url(r'^session/(?P<sid>\d+)/api/$', SessionEditUpdateAPI.as_view(), name='session_update_api'),
]
