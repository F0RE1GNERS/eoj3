"""eoj3 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from home.views import home_view
from problem.views import ProblemList, ProblemView
from submission.views import SubmissionView, StatusList
from account.views import my_login, register_view
from django.contrib.auth.views import logout
from django.views.static import serve
from .settings import UPLOAD_DIR, DEBUG
from tests.views import test_view, test_contest_view

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', home_view, name='home'),
    # url('^', include('django.contrib.auth.urls')),
    url(r'^problem/$', ProblemList.as_view(), name='problem_list'),
    url(r'^problem/(?P<pk>\d+)/$', ProblemView.as_view(), name='problem'),
    url(r'^submission/(?P<pk>\d+)/$', SubmissionView.as_view(), name='submission'),
    url(r'^contest/', include('contest.urls', namespace='contest')),
    url(r'^status/$', StatusList.as_view(), name='status'),
    url(r'^login/$', my_login, name='login'),
    url(r'^register/$', register_view, name='register'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^backstage/', include('backstage.urls', namespace='backstage')),
    url(r'^account/', include('account.urls', namespace='account')),
    url(r'^upload/(?P<path>.*)$', serve, {'document_root': UPLOAD_DIR}, name='upload'),
    url(r'^api/', include('eoj3.api_urls', namespace='api'))
]

if DEBUG:
    urlpatterns += [
        url(r'^test/', test_view, name='test'),
        url(r'^test_contest', test_contest_view, name='test_contest')
    ]