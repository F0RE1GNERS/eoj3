from django.conf.urls import url

from .views import my_password_change, MyGroup, profile_view

urlpatterns = [
    url(r'^profile/$', profile_view, name='profile'),
    url(r'^security/$', my_password_change, name='security'),
    url(r'^group/$', MyGroup.as_view(), name='group')
]