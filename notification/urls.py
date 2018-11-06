from django.conf.urls import url
import notification.views as v


app_name = 'notification'

urlpatterns = [
    url(r'^$', v.NotificationListView.as_view(), name='list'),
    url(r'^api/notified/(?P<pk>\d+)/$', v.NotificationMarkAsRead.as_view(), name='notified'),
    url(r'^api/mark_all_as_read/$', v.NotificationMarkAllAsRead.as_view(), name='mark_all_as_read'),
]