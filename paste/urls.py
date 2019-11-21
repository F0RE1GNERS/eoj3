from django.conf.urls import url

from .views import PasteListAndCreateView, PasteDetailView, PasteDeleteView

app_name = "paste"

urlpatterns = [
  url(r'^$', PasteListAndCreateView.as_view(), name='index'),
  url(r'^(?P<pk>\w+)/$', PasteDetailView.as_view(), name='detail'),
  url(r'^(?P<pk>\w+)/delete/$', PasteDeleteView.as_view(), name='delete'),
]
