from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'notification/list.jinja2'
    context_object_name = 'notifications'

    def get_queryset(self):
        return self.request.user.notifications.active()
