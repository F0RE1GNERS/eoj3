from django.conf.urls import url

import polygon.problem.views as v

urlpatterns = [
    url(r'^$', v.ProblemList.as_view(), name='problem_list'),
    url(r'^create/$', v.ProblemCreate.as_view(), name='problem_create'),

    url(r'^(?P<pk>\d+)/pull/$', v.ProblemPull.as_view(), name='problem_pull'),
    url(r'^(?P<pk>\d+)/push/$', v.ProblemPush.as_view(), name='problem_push'),

    url(r'^(?P<pk>\d+)/preview/$', v.ProblemPreview.as_view(), name='problem_preview'),
    url(r'^(?P<pk>\d+)/edit/$', v.ProblemEdit.as_view(), name='problem_edit'),
    url(r'^(?P<pk>\d+)/access/$', v.ProblemAccessManage.as_view(), name='problem_access_manage'),
    url(r'^(?P<pk>\d+)/status/$', v.ProblemStatus.as_view(), name='problem_status'),
    url(r'^(?P<pk>\d+)/rejudge/$', v.ProblemRejudge.as_view(), name='rejudge_problem'),
    url(r'^(?P<pk>\d+)/files/$', v.ProblemStaticFileList.as_view(), name='problem_static_file_list'),
    url(r'^(?P<pk>\d+)/files/add/$', v.ProblemUploadStaticFile.as_view(), name='problem_upload_static_file'),
    url(r'^(?P<pk>\d+)/files/delete/$', v.ProblemDeleteRegularFile.as_view(), name='problem_delete_static_file'),

    url(r'^(?P<pk>\d+)/program/$', v.SessionProgramList.as_view(), name='session_program_list'),
    url(r'^(?P<pk>\d+)/program/add/$', v.SessionCreateProgram.as_view(), name='session_create_program'),
    url(r'^(?P<pk>\d+)/program/import/$', v.SessionImportProgram.as_view(), name='session_import_program'),
    url(r'^(?P<pk>\d+)/program/delete/$', v.SessionDeleteProgram.as_view(), name='session_delete_program'),
    url(r'^(?P<pk>\d+)/program/update/$', v.SessionUpdateProgram.as_view(), name='session_update_program'),
    url(r'^(?P<pk>\d+)/program/used/$', v.SessionProgramUsedToggle.as_view(), name='session_program_used_toggle'),

    url(r'^(?P<pk>\d+)/case/$', v.SessionCaseList.as_view(), name='session_case_list'),
    url(r'^(?P<pk>\d+)/case/add/$', v.SessionCreateCase.as_view(), name='session_create_case'),
    url(r'^(?P<pk>\d+)/case/api/$', v.SessionCaseDataAPI.as_view(), name='session_case_data_api'),
    url(r'^(?P<pk>\d+)/case/save/$', v.SessionSaveCaseChanges.as_view(), name='session_case_save_changes'),
    url(r'^(?P<pk>\d+)/case/preview/$', v.SessionPreviewCase.as_view(), name='session_preview_case'),
    url(r'^(?P<pk>\d+)/case/reform/$', v.SessionReformCase.as_view(), name='session_reform_case'),
    url(r'^(?P<pk>\d+)/case/validate/$', v.SessionValidateCase.as_view(), name='session_validate_case'),
    url(r'^(?P<pk>\d+)/case/output/$', v.SessionOutputCase.as_view(), name='session_output_case'),
    url(r'^(?P<pk>\d+)/case/check/$', v.SessionCheckCase.as_view(), name='session_check_case'),
    url(r'^(?P<pk>\d+)/case/delete/$', v.SessionDeleteCase.as_view(), name='session_delete_case'),
    url(r'^(?P<pk>\d+)/case/download/$', v.SessionDownloadCase.as_view(), name='session_download_case'),
]
