from django.conf.urls import url

from .account.views import AccountList, AccountPrivilegeSwitch, AccountPasswordChange
from .base_views import Index
from .contest.views import ContestInvitationList, ContestInvitationCreate, ContestInvitationDelete, ContestInvitationAssign, ContestParticipantCreate
from .contest.views import ContestList, ContestCreate, ContestProfileUpdate, ContestManage, ContestParticipantDownload, ContestInvitationDownload
from .contest.views import ContestProblemDelete, ContestProblemCreate, ContestParticipantList, ContestParticipantCommentUpdate, ContestParticipantStarToggle
from .problem.views import ProblemList, ProblemVisibleSwitch, ProblemMeta, ProblemAccessAdd
from .server.views import ServerCreate, ServerUpdate, ServerList, ServerDelete, ServerRefresh, ServerEnableOrDisable, ServerUpdateToken, ServerSynchronize
from .site.views import SiteSettingsUpdate, MigrateList, OldSubmissionQuery, OldSubmissionRejudge


urlpatterns = [
    url(r'^$', Index.as_view(), name='index'),

    url(r'^account/$', AccountList.as_view(), name='account'),
    url(r'^account/privilege/(?P<pk>\d+)/$', AccountPrivilegeSwitch.as_view(), name='account_privilege_switch'),
    url(r'^account/password/(?P<pk>\d+)/$', AccountPasswordChange.as_view(), name='account_password_change'),

    url(r'^problem/$', ProblemList.as_view(), name='problem'),
    url(r'^problem/(?P<pk>\d+)/visible/$', ProblemVisibleSwitch.as_view(), name='problem_visible_switch'),
    url(r'^problem/(?P<pk>\d+)/meta/$', ProblemMeta.as_view(), name='problem_meta'),
    url(r'^problem/(?P<pk>\d+)/access/add/$', ProblemAccessAdd.as_view(), name='problem_access_add'),

    url(r'^contest/$', ContestList.as_view(), name='contest'),
    url(r'^contest/create/$', ContestCreate.as_view(), name='contest_create'),
    url(r'^contest/(?P<pk>\d+)/edit/$', ContestProfileUpdate.as_view(), name='contest_edit'),
    url(r'^contest/(?P<pk>\d+)/manage/$', ContestManage.as_view(), name='contest_manage'),
    url(r'^contest/(?P<contest_pk>\d+)/problem/(?P<contest_problem_pk>\d+)/delete/$', ContestProblemDelete.as_view(), name='contest_problem_delete'),

    url(r'^contest/(?P<contest_pk>\d+)/problem/create/$', ContestProblemCreate.as_view(), name='contest_problem_create'),
    url(r'^contest/(?P<pk>\d+)/invitation/$', ContestInvitationList.as_view(), name='contest_invitation'),
    url(r'^contest/(?P<pk>\d+)/invitation/create/$', ContestInvitationCreate.as_view(), name='contest_invitation_create'),
    url(r'^contest/(?P<pk>\d+)/invitation/(?P<invitation_pk>\d+)/delete/$', ContestInvitationDelete.as_view(), name='contest_invitation_delete'),
    url(r'^contest/(?P<pk>\d+)/invitation/(?P<invitation_pk>\d+)/assign/$', ContestInvitationAssign.as_view(), name='contest_invitation_assign'),
    url(r'^contest/(?P<pk>\d+)/invitation/download/$', ContestInvitationDownload.as_view(), name='contest_invitation_download'),
    url(r'^contest/(?P<pk>\d+)/participants/$', ContestParticipantList.as_view(), name='contest_participant'),
    url(r'^contest/(?P<pk>\d+)/participants/(?P<participant_pk>\d+)/change/$', ContestParticipantCommentUpdate.as_view(), name='contest_participant_change'),
    url(r'^contest/(?P<pk>\d+)/participants/(?P<participant_pk>\d+)/star/$', ContestParticipantStarToggle.as_view(), name='contest_participant_star_toggle'),
    url(r'^contest/(?P<pk>\d+)/participants/create/$', ContestParticipantCreate.as_view(), name='contest_participant_create'),
    url(r'^contest/(?P<pk>\d+)/participants/download/$', ContestParticipantDownload.as_view(), name='contest_participant_download'),

    url(r'^server/$', ServerList.as_view(), name='server'),
    url(r'^server/create/$', ServerCreate.as_view(), name='server_create'),
    url(r'^server/(?P<pk>\d+)/edit/$', ServerUpdate.as_view(), name='server_edit'),
    url(r'^server/(?P<pk>\d+)/delete/$', ServerDelete.as_view(), name='server_delete'),
    url(r'^server/(?P<pk>\d+)/refresh/$', ServerRefresh.as_view(), name='server_refresh'),
    url(r'^server/(?P<pk>\d+)/enable/$', ServerEnableOrDisable.as_view(), name='server_enable'),
    url(r'^server/(?P<pk>\d+)/edit/token/$', ServerUpdateToken.as_view(), name='server_update_token'),
    url(r'^server/(?P<pk>\d+)/synchronize/$', ServerSynchronize.as_view(), name='server_synchronize'),

    url(r'^site/$', SiteSettingsUpdate.as_view(), name='site'),
    url(r'^migrate/$', MigrateList.as_view(), name='migrate'),
    url(r'^migrate/code/(?P<submission_id>\d+)/', OldSubmissionQuery.as_view(), name='migrate_code'),
    url(r'^migrate/rejudge/(?P<submission_id>\d+)/', OldSubmissionRejudge.as_view(), name='migrate_rejudge'),
]
