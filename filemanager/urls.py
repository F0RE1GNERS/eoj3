from django.conf.urls import url

from filemanager.views import FileManager

app_name = "filemanager"

urlpatterns = [
  url(r'^$', FileManager.as_view(), name='index'),
]
