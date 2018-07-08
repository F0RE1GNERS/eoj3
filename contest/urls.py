from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, ContestBoundUser, DashboardView, ContestAlwaysRunningList, \
    ContestPublicToggleRegister, ContestRatings, ContestStatements
from .submission import ContestMyPastSubmissions, ContestStatus, ContestSubmit, ContestBalloon,\
    ContestSubmissionView, ContestMyStatus, ContestSubmissionAPI, ContestPenaltyDetail, ContestSubmissionClaim, \
    ContestStatusForAll, ContestBalloonClaim, ContestBalloonCancel
from .standings import ContestStandings, ContestUpdateStandings, ContestDownloadStandings, ContestDownloadCode
from .clarification import ContestClarificationView, ContestClarificationAnswer
from .activity import ActivityList, ActivityAddView, ActivityUpdateView, ActivityRegisterView, ActivityQuitView, \
    ActivityParticipantList, ActivityAdminAddUserView, ActivityAdminUpdateUserView, ActivityAddSchoolView, \
    ActivityParticipantConfirmEmailSent, ActivityParticipantConfirmComplete

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^gym/$', ContestAlwaysRunningList.as_view(), name='gym'),
    url(r'^rating/$', ContestRatings.as_view(), name='rating'),
    url(r'^(?P<cid>\d+)/$', DashboardView.as_view(), name='dashboard'),
    url(r'^(?P<cid>\d+)/standings/$', ContestStandings.as_view(), name='standings'),
    url(r'^(?P<cid>\d+)/problem/(?P<pid>\w+)/$', ContestProblemDetail.as_view(), name='problem'),
    url(r'^(?P<cid>\d+)/statements/$', ContestStatements.as_view(), name='statements'),
    url(r'^(?P<cid>\d+)/submit/(?P<pid>\w+)$', ContestSubmit.as_view(), name='submit'),
    url(r'^(?P<cid>\d+)/submission/past/(?P<pid>\w+)/$', ContestMyPastSubmissions.as_view(), name='past_submission'),
    url(r'^(?P<cid>\d+)/submission/(?P<sid>\d+)/api/$', ContestSubmissionAPI.as_view(), name='submission_api'),
    url(r'^(?P<cid>\d+)/submission/(?P<sid>\d+)/$', ContestSubmissionView.as_view(), name='submission'),
    url(r'^(?P<cid>\d+)/my/$', ContestMyStatus.as_view(), name='my'),
    url(r'^(?P<cid>\d+)/my/claim/$', ContestSubmissionClaim.as_view(), name='my_claim'),
    url(r'^(?P<cid>\d+)/status/$', ContestStatusForAll.as_view(), name='status'),
    url(r'^(?P<cid>\d+)/clarification/$', ContestClarificationView.as_view(), name='clarification'),
    url(r'^(?P<cid>\d+)/clarification/(?P<pk>\d+)/answer/$', ContestClarificationAnswer.as_view(), name='clarification_answer'),
    url(r'^(?P<cid>\d+)/invitation/$', ContestBoundUser.as_view(), name='invitation'),
    url(r'^(?P<cid>\d+)/standings/penalty/$', ContestPenaltyDetail.as_view(), name='penalty_detail'),
    url(r'^(?P<cid>\d+)/standings/update/$', ContestUpdateStandings.as_view(), name='update_standings'),
    url(r'^(?P<cid>\d+)/standings/download/$', ContestDownloadStandings.as_view(), name='download_standings'),
    url(r'^(?P<cid>\d+)/balloon/$', ContestBalloon.as_view(), name='balloon'),
    url(r'^(?P<cid>\d+)/balloon/(?P<pk>\d+)/$', ContestBalloonClaim.as_view(), name='balloon_claim'),
    url(r'^(?P<cid>\d+)/balloon/(?P<pk>\d+)/cancel/$', ContestBalloonCancel.as_view(), name='balloon_cancel'),
    url(r'^(?P<cid>\d+)/code/download/$', ContestDownloadCode.as_view(), name='download_code'),
    url(r'^(?P<cid>\d+)/register/$', ContestPublicToggleRegister.as_view(), name='public_register'),

    url(r'^activity/$', ActivityList.as_view(), name='activity_list'),
    url(r'^activity/add/$', ActivityAddView.as_view(), name='activity_add'),
    url(r'^activity/(?P<pk>\d+)/update/$', ActivityUpdateView.as_view(), name='activity_update'),
    url(r'^activity/(?P<pk>\d+)/$', ActivityRegisterView.as_view(), name='activity_register'),
    url(r'^activity/(?P<pk>\d+)/quit/$', ActivityQuitView.as_view(), name='activity_quit'),
    url(r'^activity/(?P<pk>\d+)/participants/$', ActivityParticipantList.as_view(), name='activity_participant'),
    url(r'^activity/(?P<pk>\d+)/admin/add/$', ActivityAdminAddUserView.as_view(), name='activity_admin_add'),
    url(r'^activity/(?P<pk>\d+)/admin/update/(?P<upk>\d+)/$', ActivityAdminUpdateUserView.as_view(), name='activity_admin_update'),
    url(r'^activity/school/add/$', ActivityAddSchoolView.as_view(), name='activity_add_school'),
    url(r'^activity/(?P<pk>\d+)/confirm/$', ActivityParticipantConfirmEmailSent.as_view(), name='activity_confirm_email'),
    url(r'^activity/confirm/complete/$', ActivityParticipantConfirmComplete.as_view(), name='activity_confirm_complete'),
]
