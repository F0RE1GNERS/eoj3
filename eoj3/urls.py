import re

from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import logout
from django.views.static import serve

from migrate.views import migrate_view
from utils.comment import login_required_post_comment
import django_comments_xtd.api as comment_xtd_api

from account.views import my_login, RegisterView, FeedbackView
from blog.views import GenericView
from home.views import home_view, faq_view, TestView
from problem.views import make_payment_for_full_report, case_download_link
from submission.views import SubmissionRejudgeView
from tests.views import test_view, test_contest_view
from .settings import UPLOAD_DIR, DEBUG, STATIC_DIR, MEDIA_URL, MEDIA_ROOT

UPLOAD_ROOT = '/upload/'
STATIC_ROOT = '/static/'


def force_closed():
    return {"force_closed": True}


urlpatterns = [
    url(r'^login/$', my_login, name='login'),
    url(r'^contest/', include('contest.urls', namespace='contest')),
    url(r'^backstage/', include('backstage.urls', namespace='backstage')),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^logout/$', logout, name='logout'),

    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('eoj3.api_urls', namespace='api')),
    url(r'^$', home_view, name='home'),
    url(r'^faq/$', faq_view, name='faq'),
    url(r'^problem/', include('problem.urls', namespace='problem'), kwargs=force_closed()),
    url(r'^rejudge/(?P<pk>\d+)/$', SubmissionRejudgeView.as_view(), name='rejudge'),
    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^account/', include('account.urls', namespace='account')),
    url(r'^generic/(?P<pk>\d+)/$', GenericView.as_view(), name='generic', kwargs=force_closed()),
    url(r'^blog/', include('blog.urls', namespace='blog'), kwargs=force_closed()),
    url(r'^feedback/', FeedbackView.as_view(), name='feedback'),
    url(r'^polygon/', include('polygon.urls', namespace='polygon')),
    url(r'^message/', include('message.urls', namespace='message')),
    url(r'^notification/', include('notification.urls', namespace='notification')),
    url(r'^migrate/$', migrate_view, name='migrate'),
    url(r'^pay/report/', make_payment_for_full_report, name='pay_report'),
    url(r'^case/download/$', case_download_link, name='download_case'),
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
        url(r'^test/', test_view, name='test'),
        url(r'^test_contest', test_contest_view, name='test_contest'),
        url(r'^%s(?P<path>.*)$' % re.escape(STATIC_ROOT.lstrip('/')), serve, name='static',
            kwargs={'document_root': STATIC_DIR}),
        url(r'^%s(?P<path>.*)$' % re.escape(UPLOAD_ROOT.lstrip('/')), serve, name='upload',
            kwargs={'document_root': UPLOAD_DIR}),
        # url(r'^%s(?P<path>.*)$' % re.escape(UPLOAD_ROOT.lstrip('/')), serve, name='media',
        #     kwargs={'document_root': MEDIA_DIR}),
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^t/', TestView.as_view())
    ] + static(MEDIA_URL, document_root=MEDIA_ROOT)


handler403 = 'home.views.forbidden_view'
handler404 = 'home.views.not_found_view'
# handler500 = 'home.views.server_error_view'
