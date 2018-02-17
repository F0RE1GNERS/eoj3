from django.conf.urls import url

from polygon.problem.views import base, asset, case, revision, statement


urlpatterns = [
    url(r'^$', base.ProblemList.as_view(), name='problem_list'),
    url(r'^create/$', base.ProblemCreate.as_view(), name='problem_create'),

    url(r'^(?P<pk>\d+)/revision/create/$', revision.RevisionCreateView.as_view(), name='revision_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/$', revision.RevisionUpdateView.as_view(), name='revision_view'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/fork/$', revision.RevisionForkView.as_view(), name='revision_fork'),

    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/$', asset.AssetList.as_view(), name='revision_asset'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/create/$', asset.AssetCreateView.as_view(), name='revision_asset_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/(?P<apk>\d+)/update/$$', asset.AssetUpdateView.as_view(),
        name='revision_asset_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/asset/(?P<apk>\d+)/rename/$$', asset.AssetRenameView.as_view(),
        name='revision_asset_rename'),

    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/$', statement.StatementList.as_view(), name='revision_statement'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/create/$', statement.StatementCreateView.as_view(),
        name='revision_statement_create'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/update/$$', statement.StatementUpdateView.as_view(),
        name='revision_statement_update'),
    url(r'^(?P<pk>\d+)/revision/(?P<rpk>\d+)/statement/(?P<spk>\d+)/activate/$$', statement.StatementActivateView.as_view(),
        name='revision_statement_activate'),
]
