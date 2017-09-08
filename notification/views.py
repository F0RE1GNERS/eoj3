from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView, status, Response


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'notification/list.jinja2'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return self.request.user.notifications.active()

    def get(self, request, *args, **kwargs):
        self.request.user.notifications.mark_all_as_read()
        return super().get(request, *args, **kwargs)


class NotificationMarkAllAsRead(LoginRequiredMixin, APIView):

    def post(self, request):
        request.user.notifications.mark_all_as_read()
        return Response(status=status.HTTP_200_OK)


class NotificationLiveUpdater(LoginRequiredMixin, APIView):

    def get(self, request):
        return Response({
            'unread_count': request.user.notifications.unread().count()
        })
