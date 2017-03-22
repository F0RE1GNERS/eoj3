from django.conf.urls import url

from .views import my_password_change, profile_view

urlpatterns = [
    url(r'^profile/$', profile_view, name='profile'),
    url(r'^security/$', my_password_change, name='security'),
]