from django.db import models
from account.models import User


class ConversationManager(models.Manager):
    def start_conversation(self, msg, recipient):  # type: (Message, User) -> Conversation
        c = self.create()
        c.add_users(msg.sender, recipient)
        c.messages.add(msg)
        return c


class Conversation(models.Model):
    last_update = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(User, through='UserConversation')

    class Meta:
        ordering = ['-last_update']

    # def add_users(self, *users: User):
    #     for user in users:
    #         UserConversation.objects.create(conversation=self, user=user)
    #
    # def mark_all_read(self, user: User):
    #     uc: UserConversation = UserConversation.objects.filter(conversation=self).filter(user=user).first()
    #     if uc:
    #         uc.unread = False
    #         uc.save()

    objects = ConversationManager()


class UserConversation(models.Model):
    user = models.ForeignKey(User)
    conversation = models.ForeignKey(Conversation)
    unread = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'conversation']


class Message(models.Model):
    content = models.TextField('content', blank=True)
    sender = models.ForeignKey(User, related_name='sent_messages')
    # recipient = models.ForeignKey(User, related_name='received_messages')
    sent_time = models.DateTimeField(auto_now_add=True)
    # unread = models.BooleanField(default=True)
    conversation = models.ForeignKey(Conversation, related_name='messages', null=True)



