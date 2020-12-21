import django_comments_xtd.api as comment_xtd_api
from django.conf.urls import url, include
from django.contrib import admin
from django.views.static import serve

from account.profile import ProfileView, ProgressTreeView
from account.views import my_login, RegisterView, FeedbackView
from blog.views import GetRewardsView
from home.museum import museum_view
from home.search import search_view
from home.views import home_view, faq_view, TestView, forbidden_view, not_found_view, server_error_view, PasteView
from migrate.views import migrate_view
from tests.views import judge_mock, query_mock, query_report_mock
from utils.auth_view import logout
from utils.comment import login_required_post_comment
from utils.site_settings import force_closed
from utils.serve_nginx import serve_with_nginx
from .settings import DEBUG, UPLOAD_DIR, STATIC_DIR, MEDIA_ROOT, GENERATE_DIR


urlpatterns = [
  url(r'^login/$', my_login, name='login'),
  url(r'^contest/', include('contest.urls', namespace='contest')),
  url(r'^backstage/', include('backstage.urls', namespace='backstage')),
  url(r'^captcha/', include('captcha.urls')),
  url(r'^logout/$', logout, name='logout'),
  url(r'^search/$', search_view, name='search', kwargs=force_closed()),
  url(r'^mirror/', include('filemanager.urls', namespace='filemanager'), kwargs=force_closed()),
  url(r'^admin/', admin.site.urls),
  url(r'^api/', include('api.urls', namespace='api')),
  url(r'^$', home_view, name='home'),
  url(r'^faq/$', faq_view, name='faq'),
  url(r'^problem/', include('problem.urls', namespace='problem'), kwargs=force_closed()),
  url(r'^register/$', RegisterView.as_view(), name='register'),
  url(r'^account/', include('account.urls', namespace='account')),
  url(r'^blog/', include('blog.urls', namespace='blog'), kwargs=force_closed()),
  url(r'^feedback/', FeedbackView.as_view(), name='feedback'),
  url(r'^polygon/', include('polygon.urls', namespace='polygon'), kwargs=force_closed()),
  url(r'^notification/', include('notification.urls', namespace='notification')),
  url(r'^migrate/$', migrate_view, name='migrate', kwargs=force_closed()),
  url(r'^museum/$', museum_view, name='museum'),
  url(r'^paste/$', PasteView.as_view(), name='pastebin'),  # TODO: delete?
  url(r'^h/', include('paste.urls', namespace='paste'), kwargs=force_closed()),
  url(r'^profile/progress/(?P<pk>\d+)/$', ProgressTreeView.as_view(), name='progress', kwargs=force_closed()),
  url(r'^profile/(?P<pk>\d+)/$', ProfileView.as_view(), name='profile', kwargs=force_closed()),
  # url(r'^i18n/', include('django.conf.urls.i18n')),  # TODO: delete?
  url(r'^reward/(?P<pk>\d+)/$', GetRewardsView.as_view(), name='rewardslist', kwargs=force_closed()),
]

urlpatterns += [
  url(r'^403/(?P<exception>\w+)/$', forbidden_view),
  url(r'^404/$', not_found_view),
  url(r'^500/$', server_error_view),
]

urlpatterns += [
  url(r'^comment/post/$', login_required_post_comment, name='comments-post-comment', kwargs=force_closed()),
  url(r'^comment/api/feedback/$', comment_xtd_api.ToggleFeedbackFlag.as_view(),
      name='comments-xtd-api-feedback', kwargs=force_closed()),
  url(r'^comment/api/flag/$', comment_xtd_api.CreateReportFlag.as_view(),
      name='comments-xtd-api-flag', kwargs=force_closed()),
]



if DEBUG:
  import debug_toolbar

  urlpatterns += [
    url(r'^media/(?P<path>.*)$', serve, name='media', kwargs={'document_root': MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, name='static', kwargs={'document_root': STATIC_DIR}),
    url(r'^upload/(?P<path>.*)$', serve, name='upload', kwargs={'document_root': UPLOAD_DIR}),
    url(r'^generate/(?P<path>.*)$', serve, name='generate', kwargs={'document_root': GENERATE_DIR}),
    url(r'^__debug__/', include(debug_toolbar.urls)),
    url(r'^t/', TestView.as_view())
  ]
  urlpatterns += [
    # mock judge's response
    url(r'^judge$', judge_mock),
    url(r'^query$', query_mock),
    url(r'^query/report$', query_report_mock),
  ]
else:
  urlpatterns += [
    url(r'^media/(?P<path>.*)$', serve_with_nginx, name='media', kwargs={'root_name': 'media'}),
    url(r'^static/(?P<path>.*)$', serve_with_nginx, name='static', kwargs={'root_name': 'static'}),
    url(r'^upload/(?P<path>.*)$', serve_with_nginx, name='upload', kwargs={'root_name': 'upload'}),
    url(r'^generate/(?P<path>.*)$', serve_with_nginx, name='generate', kwargs={'root_name': 'generate'})
  ]

handler403 = 'home.views.forbidden_view'
handler404 = 'home.views.not_found_view'
handler500 = 'home.views.server_error_view'
