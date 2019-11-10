from django.conf.urls import url

from backstage.email.views import EmailCreateView, EmailUpdateView, EmailAddRecipient, EmailDeleteRecipient, \
  EmailPreview, EmailSend, EmailRecipientErrorReport
from backstage.email.views import EmailList
from .account.views import AccountList, AccountPrivilegeSwitch, AccountPasswordChange, AccountPolygonSwitch, \
  AccountActiveSwitch, \
  AccountSchoolList, AccountAddSchool, AccountEditSchool
from .base_views import Index
from .blog.views import BlogList, BlogRecommendSwitch, BlogVisibleSwitch
from .contest.views import ContestList, ContestApplyRatingChanges, ContestWithdrawRatingChanges, \
  ApplyGlobalChangesToRating
from .problem.views import ProblemList, ProblemVisibleSwitch, ProblemTagList, ProblemTagCreate, ProblemTagEdit, \
  ProblemArchiveList, ProblemArchiveEdit, ProblemArchiveCreate, ProblemSourceBatchEdit, ProblemTagDelete
from .server.views import ServerCreate, ServerUpdate, ServerList, ServerDelete, ServerRefresh, ServerEnableOrDisable, \
  ServerUpdateToken, ServerSynchronize, ServerProblemStatusList, ServerSemaphoreReset, RejudgeAllCrashedSubmission
from .site.views import SiteSettingsUpdate

app_name = "backstage"

urlpatterns = [
  url(r'^$', Index.as_view(), name='index'),

  url(r'^account/$', AccountList.as_view(), name='account'),
  url(r'^account/privilege/(?P<pk>\d+)/$', AccountPrivilegeSwitch.as_view(), name='account_privilege_switch'),
  url(r'^account/polygon/(?P<pk>\d+)/$', AccountPolygonSwitch.as_view(), name='account_polygon_switch'),
  url(r'^account/password/(?P<pk>\d+)/$', AccountPasswordChange.as_view(), name='account_password_change'),
  url(r'^account/active/(?P<pk>\d+)/$', AccountActiveSwitch.as_view(), name='account_active_switch'),
  url(r'^account/school/$', AccountSchoolList.as_view(), name='account_school'),
  url(r'^account/school/add/$', AccountAddSchool.as_view(), name='account_school_add'),
  url(r'^account/school/(?P<pk>\d+)/edit/$', AccountEditSchool.as_view(), name='account_school_edit'),

  url(r'^problem/$', ProblemList.as_view(), name='problem'),
  url(r'^problem/(?P<pk>\d+)/visible/$', ProblemVisibleSwitch.as_view(), name='problem_visible_switch'),
  url(r'^tags/$', ProblemTagList.as_view(), name='tags'),
  url(r'^tags/add/$', ProblemTagCreate.as_view(), name='tag_add'),
  url(r'^tags/(?P<pk>\d+)/edit/$', ProblemTagEdit.as_view(), name='tag_edit'),
  url(r'^tags/(?P<pk>\d+)/delete/$', ProblemTagDelete.as_view(), name='tag_delete'),
  url(r'^archive/$', ProblemArchiveList.as_view(), name='archive'),
  url(r'^archive/add/$', ProblemArchiveCreate.as_view(), name='archive_add'),
  url(r'^archive/(?P<pk>\d+)/edit/$', ProblemArchiveEdit.as_view(), name='archive_edit'),
  url(r'^problem/source/$', ProblemSourceBatchEdit.as_view(), name='source_edit'),

  url(r'^contest/$', ContestList.as_view(), name='contest'),
  url(r'^contest/(?P<cid>\d+)/ratings/apply/$', ContestApplyRatingChanges.as_view(), name='contest_apply_ratings'),
  url(r'^contest/(?P<cid>\d+)/ratings/withdraw/$', ContestWithdrawRatingChanges.as_view(),
      name='contest_withdraw_ratings'),
  url(r'^contest/ratings/global/$', ApplyGlobalChangesToRating.as_view(), name='contest_apply_ratings_global'),

  url(r'^server/$', ServerList.as_view(), name='server'),
  url(r'^server/create/$', ServerCreate.as_view(), name='server_create'),
  url(r'^server/(?P<pk>\d+)/edit/$', ServerUpdate.as_view(), name='server_edit'),
  url(r'^server/(?P<pk>\d+)/delete/$', ServerDelete.as_view(), name='server_delete'),
  url(r'^server/(?P<pk>\d+)/refresh/$', ServerRefresh.as_view(), name='server_refresh'),
  url(r'^server/(?P<pk>\d+)/enable/$', ServerEnableOrDisable.as_view(), name='server_enable'),
  url(r'^server/(?P<pk>\d+)/edit/token/$', ServerUpdateToken.as_view(), name='server_update_token'),
  url(r'^server/(?P<pk>\d+)/status/$', ServerProblemStatusList.as_view(), name='server_problem_status'),
  url(r'^server/(?P<pk>\d+)/synchronize/$', ServerSynchronize.as_view(), name='server_synchronize'),
  url(r'^server/semaphore/reset/$', ServerSemaphoreReset.as_view(), name='server_semaphore_reset'),
  url(r'^server/rejudge/crashed/$', RejudgeAllCrashedSubmission.as_view(), name='rejudge_crashed_submission'),

  url(r'^site/$', SiteSettingsUpdate.as_view(), name='site'),

  url(r'^blog/$', BlogList.as_view(), name='blog'),
  url(r'^blog/(?P<pk>\d+)/visible/$', BlogVisibleSwitch.as_view(), name='blog_visible_switch'),
  url(r'^blog/(?P<pk>\d+)/recommend/$', BlogRecommendSwitch.as_view(), name='blog_recommend_switch'),

  url(r'^email/$', EmailList.as_view(), name='email'),
  url(r'^email/create/$', EmailCreateView.as_view(), name='email_create'),
  url(r'^email/(?P<eid>\d+)/update/$', EmailUpdateView.as_view(), name='email_update'),
  url(r'^email/(?P<eid>\d+)/recipient/add/$', EmailAddRecipient.as_view(), name='email_recipient_add'),
  url(r'^email/recipient/(?P<pk>\d+)/error/$', EmailRecipientErrorReport.as_view(), name='email_recipient_error'),
  url(r'^email/recipient/(?P<pk>\d+)/delete/$', EmailDeleteRecipient.as_view(),
      name='email_recipient_delete'),
  url(r'^email/(?P<eid>\d+)/preview/$', EmailPreview.as_view(), name='email_preview'),
  url(r'^email/(?P<eid>\d+)/send/$', EmailSend.as_view(), name='email_send'),
]
