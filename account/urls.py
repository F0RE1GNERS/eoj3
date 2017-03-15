from django.conf.urls import url

from .views import security_view

urlpatterns = [
    url(r'^$', security_view, name='security'),
]