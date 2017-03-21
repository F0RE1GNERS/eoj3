from django.conf.urls import url

from .base_views import index
from .problem.views import ProblemCreate, ProblemUpdate, ProblemList, testdata, problem_delete
from .group.views import GroupList, GroupUpdate, GroupCreate, GroupManage, group_member_delete
from .contest.views import ContestList, ContestCreate, ContestProfileUpdate, ContestManage
from .contest.views import contest_problem_delete, contest_problem_create, ContestParticipantList
from .contest.views import ContestInvitationList, contest_invitation_create, contest_invitation_delete, contest_invitation_assign
from .server.views import ServerCreate, ServerUpdate, ServerList, server_delete

urlpatterns = [
    url(r'^$', index, name='index'),

    url(r'^problem/$', ProblemList.as_view(), name='problem'),
    url(r'^problem/create/$', ProblemCreate.as_view(), name='problem_create'),
    url(r'^problem/(?P<pk>\d+)/edit/', ProblemUpdate.as_view(), name='problem_edit'),
    url(r'^problem/(?P<pk>\d+)/testdata/', testdata, name='problem_testdata'),
    url(r'^problem/(?P<pk>\d+)/delete/', problem_delete, name='problem_delete'),

    url(r'^group/$', GroupList.as_view(), name='group'),
    url(r'^group/create/$', GroupCreate.as_view(), name='group_create'),
    url(r'^group/(?P<pk>\d+)/edit/', GroupUpdate.as_view(), name='group_edit'),
    url(r'^group/(?P<pk>\d+)/manage/', GroupManage.as_view(), name='group_manage'),
    url(r'^group/(?P<pk>\d+)/member/(?P<membership_pk>\d+)/delete/', group_member_delete, name='group_delete'),

    url(r'^contest/$', ContestList.as_view(), name='contest'),
    url(r'^contest/create/$', ContestCreate.as_view(), name='contest_create'),
    url(r'^contest/(?P<pk>\d+)/edit/', ContestProfileUpdate.as_view(), name='contest_edit'),
    url(r'^contest/(?P<pk>\d+)/manage/', ContestManage.as_view(), name='contest_manage'),
    url(r'^contest/(?P<contest_pk>\d+)/problem/(?P<contest_problem_pk>\d+)/delete/', contest_problem_delete, name='contest_problem_delete'),

    url(r'^contest/(?P<contest_pk>\d+)/problem/create/', contest_problem_create, name='contest_problem_create'),
    url(r'^contest/(?P<pk>\d+)/invitation/$', ContestInvitationList.as_view(), name='contest_invitation'),
    url(r'^contest/(?P<pk>\d+)/invitation/create/', contest_invitation_create, name='contest_invitation_create'),
    url(r'^contest/(?P<pk>\d+)/invitation/(?P<invitation_pk>\d+)/delete/', contest_invitation_delete, name='contest_invitation_delete'),
    url(r'^contest/(?P<pk>\d+)/invitation/(?P<invitation_pk>\d+)/assign/', contest_invitation_assign, name='contest_invitation_assign'),
    url(r'^contest/(?P<pk>\d+)/participants/', ContestParticipantList.as_view(), name='contest_participant'),

    url(r'^server/$', ServerList.as_view(), name='server'),
    url(r'^server/create/', ServerCreate.as_view(), name='server_create'),
    url(r'^server/edit/(?P<pk>\d+)/', ServerUpdate.as_view(), name='server_edit'),
    url(r'^server/delete/(?P<pk>\d+)/', server_delete, name='server_delete'),
]
