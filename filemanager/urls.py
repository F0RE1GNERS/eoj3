from django.conf.urls import url

from filemanager.views import FileManager


urlpatterns = [
    url(r'^$', FileManager.as_view(), name='index'),
]
