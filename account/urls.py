from django.conf.urls import url

from utils.site_settings import force_closed
from . import views

app_name = "account"

urlpatterns = [
  url(r'^settings/profile/$', views.UpdateProfileView.as_view(), name='profile', kwargs=force_closed()),
  url(r'^settings/security/$', views.my_password_change, name='security', kwargs=force_closed()),
  url(r'^settings/preference/$', views.UpdatePreferencesView.as_view(), name='preference', kwargs=force_closed()),
  url(r'^settings/username/update/$', views.ChangeUsernameView.as_view(), name='change_username'),
  url(r'^password_reset/$', views.my_password_reset, name='reset_password'),
  url(r'^password_reset_done/$', views.my_password_reset_done, name='password_reset_done'),
  url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
      views.my_password_reset_confirm, name='password_reset_confirm'),
  url(r'^ban/(?P<user_id>[0-9]+)/$', views.BanAccount.as_view(), name='ban_account'),
]
