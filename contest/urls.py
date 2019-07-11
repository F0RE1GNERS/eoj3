from django.conf.urls import url

from .views import ContestList, ContestProblemDetail, ContestBoundUser, DashboardView, ContestGymList, \
    ContestPublicToggleRegister, ContestRatings, ContestStatements, ContestVirtualParticipantJoin
from .submission import ContestMyPastSubmissions, ContestStatus, ContestSubmit, ContestBalloon,\
    ContestSubmissionView, ContestMyStatus, ContestSubmissionAPI, ContestPenaltyDetail, ContestSubmissionClaim, \
    ContestStatusForAll, ContestBalloonClaim, ContestBalloonCancel
from .standings import ContestStandings, ContestUpdateStandings, ContestDownloadStandings, ContestDownloadCode, \
    ContestStandingsTestSys
from .clarification import ContestClarificationView, ContestClarificationAnswer, ContestClarificationList, ContestNotificationCheck
from .activity import ActivityList, ActivityAddView, ActivityUpdateView, ActivityRegisterView, ActivityQuitView, \
    ActivityParticipantList, ActivityAdminAddUserView, ActivityAdminUpdateUserView, ActivityAddSchoolView, \
    ActivityParticipantConfirmEmailSent, ActivityParticipantConfirmComplete

app_name = "contest"

urlpatterns = [
    url(r'^$', ContestList.as_view(), name='list'),
    url(r'^gym/$', ContestGymList.as_view(), name='gym'),
    url(r'^rating/$', ContestRatings.as_view(), name='rating'),
    url(r'^(?P<cid>\d+)/$', DashboardView.as_view(), name='dashboard'),
    url(r'^(?P<cid>\d+)/check/$', ContestNotificationCheck.as_view(), name='check'),
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
    url(r'^(?P<cid>\d+)/question/$', ContestClarificationList.as_view(), name='question'),
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
    url(r'^(?P<cid>\d+)/report/testsys/$', ContestStandingsTestSys.as_view(), name='report_testsys'),
    url(r'^(?P<cid>\d+)/register/$', ContestPublicToggleRegister.as_view(), name='public_register'),
]
