from django.conf.urls import url

import polygon.problem.views as v

urlpatterns = [
    url(r'^$', v.ProblemList.as_view(), name='problem_list'),
    url(r'^(?P<pk>\d+)/preview/$', v.ProblemPreview.as_view(), name='problem_preview'),
    url(r'^(?P<pk>\d+)/edit/$', v.ProblemEdit.as_view(), name='problem_edit'),
    url(r'^(?P<pk>\d+)/access/$', v.ProblemAccessManage.as_view(), name='problem_access_manage'),
    url(r'^(?P<pk>\d+)/status/$', v.ProblemStatus.as_view(), name='problem_status'),
    url(r'^(?P<pk>\d+)/rejudge/$', v.ProblemRejudge.as_view(), name='rejudge_problem'),
    url(r'^(?P<pk>\d+)/files/$', v.ProblemStaticFileList.as_view(), name='problem_static_file_list'),
    url(r'^(?P<pk>\d+)/files/add/$', v.ProblemUploadStaticFile.as_view(), name='problem_upload_static_file'),
    url(r'^(?P<pk>\d+)/files/delete/$', v.ProblemDeleteRegularFile.as_view(), name='problem_delete_static_file'),
]
