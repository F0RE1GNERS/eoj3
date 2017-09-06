from django.conf.urls import url
import notification.views as v


urlpatterns = [
    url(r'^$', v.NotificationListView.as_view(), name='list'),
]