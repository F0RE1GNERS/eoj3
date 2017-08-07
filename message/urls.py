from django.conf.urls import url
from .views import StartConversationView, ConversationListView
urlpatterns = [
    url(r'^c/create/$', StartConversationView.as_view()),
    url(r'^c/$', ConversationListView.as_view())
]