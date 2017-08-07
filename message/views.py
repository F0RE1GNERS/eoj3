from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import HttpResponseRedirect
from django.views.generic import FormView, ListView
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .forms import StartConversationForm
from .models import Conversation, UserConversation, Message


class StartConversationView(LoginRequiredMixin, FormView):
    template_name = 'message/_new_conversation.jinja2'
    form_class = StartConversationForm

    def form_valid(self, form):
        c = form.create(sender=self.request.user)
        return HttpResponseRedirect(self.request.get_full_path())


class ConversationListView(LoginRequiredMixin, ListView):
    template_name = 'message/conversation.jinja2'
    context_object_name = 'conversation_list'

    def get_queryset(self):
        return self.request.user.conversation_set.all()


class ReplyAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        content = request.data.get('content', '')
        c = get_object_or_404(Conversation, pk=pk)
        uc_qs = UserConversation.objects.filter(conversation=c).all()
        if uc_qs.filter(user=request.user).exists() is False:
            return Response(status=status.HTTP_403_FORBIDDEN)
        msg = Message.objects.create(sender=request.user, content=content)
        c.messages.add(msg)
        for uc in uc_qs.exclude(user=request.user):
            uc.unread = True
            uc.save()
        return Response(status=status.HTTP_200_OK)
