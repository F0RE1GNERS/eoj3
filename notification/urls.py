from django.conf.urls import url
import notification.views as v


urlpatterns = [
    url(r'^$', v.NotificationListView.as_view(), name='list'),
    url(r'^api/mark_all_as_read/$', v.NotificationMarkAllAsRead.as_view(), name='mark_all_as_read'),
    url(r'^api/hot/$', v.NotificationLiveUpdater.as_view(), name='hot'),
]