from django.conf.urls import url
from .views import StartConversationView, ConversationListView

app_name = "message"

urlpatterns = [
    url(r'^c/create/$', StartConversationView.as_view()),
    url(r'^c/$', ConversationListView.as_view())
]