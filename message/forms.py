from django import forms
from account.models import User
from .models import Conversation, Message


class StartConversationForm(forms.Form):
    recipient_pk = forms.IntegerField(label='to', help_text='username')
    content = forms.CharField(label='content')

    def clean_recipient_pk(self):
        recipient_pk = self.cleaned_data['recipient_pk']
        try:
            recipient = User.objects.get(pk=recipient_pk)
        except User.DoesNotExist:
            raise forms.ValidationError("The username your entered doesn't exist.")
        self.cleaned_data['recipient'] = recipient
        return recipient_pk

    def create(self, sender: User):
        msg = Message.objects.create(sender=sender, content=self.cleaned_data['content'])
        c = Conversation.objects.start_conversation(msg=msg, recipient=self.cleaned_data['recipient'])
        return c
