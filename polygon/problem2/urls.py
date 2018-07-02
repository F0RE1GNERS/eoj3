from django.conf.urls import url

from polygon.problem2.views import base, asset, case, program, revision, statement, task

urlpatterns = [
    url(r'^$', base.ProblemList.as_view(), name='problem_list_2'),
    url(r'^create/$', base.ProblemCreate.as_view(), name='problem_create_2'),
    url(r'^(?P<pk>\d+)/info/$', base.ProblemBasicInfoManage.as_view(), name='problem_basic_info'),
    url(r'^(?P<pk>\d+)/status/$', base.ProblemStatus.as_view(), name='problem_status'),
    url(r'^(?P<pk>\d+)/rejudge/$', base.ProblemRejudge.as_view(), name='rejudge_problem'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/create/$', revision.RevisionCreateView.as_view(), name='revision_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/$', revision.RevisionUpdateView.as_view(), name='revision_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/fork/$', revision.RevisionForkView.as_view(), name='revision_fork'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/confirm/$', revision.RevisionConfirmView.as_view(), name='revision_confirm'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/discard/$', revision.RevisionDiscardView.as_view(), name='revision_discard'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/$', asset.AssetList.as_view(), name='revision_asset'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/create/$', asset.AssetCreateView.as_view(),
        name='revision_asset_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/(?P<apk>\d+)/update/$', asset.AssetUpdateView.as_view(),
        name='revision_asset_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/(?P<apk>\d+)/rename/$', asset.AssetRenameView.as_view(),
        name='revision_asset_rename'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/(?P<apk>\d+)/delete/$', asset.AssetDeleteView.as_view(),
        name='revision_asset_delete'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/$', statement.StatementList.as_view(),
        name='revision_statement'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/create/$', statement.StatementCreateView.as_view(),
        name='revision_statement_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/$', statement.StatementPreview.as_view(),
        name='revision_statement_preview'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/update/$', statement.StatementUpdateView.as_view(),
        name='revision_statement_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/activate/$',
        statement.StatementActivateView.as_view(),
        name='revision_statement_activate'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/delete/$', statement.StatementDeleteView.as_view(),
        name='revision_statement_delete'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/$', program.ProgramList.as_view(), name='revision_program'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/create/$', program.ProgramCreateView.as_view(),
        name='revision_program_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/(?P<ppk>\d+)/$', program.ProgramPreview.as_view(),
        name='revision_program_preview'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/(?P<ppk>\d+)/update/$', program.ProgramUpdateView.as_view(),
        name='revision_program_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/(?P<ppk>\d+)/toggle/$', program.ProgramActiveToggleView.as_view(),
        name='revision_program_toggle'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/(?P<ppk>\d+)/delete/$', program.ProgramDeleteView.as_view(),
        name='revision_program_delete'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/program/import/$', program.ProgramImportView.as_view(),
        name='revision_program_import'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/$', case.CaseList.as_view(), name='revision_case'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/create/$', case.CaseCreateView.as_view(),
        name='revision_case_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/(?P<cpk>\d+)/update/info/$', case.CaseUpdateInfoView.as_view(),
        name='revision_case_update_info'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/(?P<cpk>\d+)/update/$', case.CaseUpdateFileView.as_view(),
        name='revision_case_update_file'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/(?P<cpk>\d+)/delete/$', case.CaseDeleteView.as_view(),
        name='revision_case_delete'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/(?P<cpk>\d+)/preview/$', case.CaseFullInputOutputView.as_view(),
        name='revision_case_preview'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/order/natural/$', case.CaseNaturalizeOrderView.as_view(),
        name='revision_case_order_natural'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/order/move/$', case.CaseMoveOrderView.as_view(),
        name='revision_case_order_move'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/delete/$', case.CaseDeleteSelectedView.as_view(),
        name='revision_case_delete'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/output/$', case.CaseRunSelectedOutput.as_view(),
        name='revision_case_run_output'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/validate/$', case.CaseValidateInput.as_view(),
        name='revision_case_validate_input'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/check/$', case.CaseCheckView.as_view(),
        name='revision_case_check'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/pack/$', case.CasePackAsZipView.as_view(),
        name='revision_case_pack'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/toggle/sample/$', case.CaseToggleSampleView.as_view(),
        name='revision_case_toggle_sample'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/toggle/pretest/$', case.CaseTogglePretestView.as_view(),
        name='revision_case_toggle_pretest'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/case/group/assign/$', case.CaseAssignGroupView.as_view(),
        name='revision_case_group_assign'),
]

urlpatterns += [
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/task/$', task.TaskList.as_view(), name='revision_task'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/task/(?P<tpk>\d+)/$', task.TaskPreview.as_view(), name='revision_task_preview'),
]