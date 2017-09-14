from django.conf.urls import url
from . import views
from .payment import PaymentList

urlpatterns = [
    url(r'^settings/profile/$', views.UpdateProfileView.as_view(), name='profile'),
    url(r'^settings/security/$', views.my_password_change, name='security'),
    url(r'^settings/preference/$', views.UpdatePreferencesView.as_view(), name='preference'),
    url(r'^settings/username/update/$', views.change_username_view, name='change_username'),
    url(r'^settings/payment/$', PaymentList.as_view(), name='payment'),
    url(r'^password_reset/$', views.my_password_reset, name='reset_password'),
    url(r'^password_reset_done/$', views.my_password_reset_done, name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.my_password_reset_confirm, name='password_reset_confirm'),
    url(r'^settings/migrate/$', views.migrate_from_old, name='migrate'),
]

