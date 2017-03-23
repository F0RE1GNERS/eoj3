from django.conf.urls import url

from .base_views import Index
from .problem.views import ProblemCreate, ProblemUpdate, ProblemList, TestData, ProblemDelete
from .contest.views import ContestList, ContestCreate, ContestProfileUpdate, ContestManage
from .contest.views import ContestProblemDelete, ContestProblemCreate, ContestParticipantList
from .contest.views import ContestInvitationList, ContestInvitationCreate, ContestInvitationDelete, ContestInvitationAssign
from .server.views import ServerCreate, ServerUpdate, ServerList, ServerDelete, ServerRefresh
from .account.views import AccountList, AccountPrivilegeSwitch

urlpatterns = [
    url(r'^$', Index.as_view(), name='index'),

    url(r'^account/$', AccountList.as_view(), name='account'),
    url(r'^account/privilege/(?P<pk>\d+)/', AccountPrivilegeSwitch.as_view(), name='account_privilege_switch'),

    url(r'^problem/$', ProblemList.as_view(), name='problem'),
    url(r'^problem/create/$', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/(?P<pk>\d+)/edit/$', ProblemUpdate.as_view(), name='problem_edit'),
    url(r'^problem/(?P<pk>\d+)/testdata/$', TestData.as_view(), name='problem_testdata'),
    url(r'^problem/(?P<pk>\d+)/delete/$', ProblemDelete.as_view(), name='problem_delete'),

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
    url(r'^contest/(?P<pk>\d+)/participants/$', ContestParticipantList.as_view(), name='contest_participant'),

    url(r'^server/$', ServerList.as_view(), name='server'),
    url(r'^server/create/$', ServerCreate.as_view(), name='server_create'),
    url(r'^server/(?P<pk>\d+)/edit/$', ServerUpdate.as_view(), name='server_edit'),
    url(r'^server/(?P<pk>\d+)/delete/$', ServerDelete.as_view(), name='server_delete'),
    url(r'^server/(?P<pk>\d+)/refresh/$', ServerRefresh.as_view(), name='server_refresh')
]
