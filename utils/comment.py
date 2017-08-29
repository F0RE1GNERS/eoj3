from django import forms
from django.dispatch import receiver
from django_comments.models import CommentFlag
from django_comments.signals import comment_was_flagged
from django_comments_xtd.forms import XtdCommentForm

from account.permissions import is_admin_or_root


class CommentForm(XtdCommentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['email'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['url'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['honeypot'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['followup'] = forms.BooleanField(widget=forms.HiddenInput)
        self.fields['comment'].widget = forms.Textarea(attrs={'class': 'markdown'})


@receiver(comment_was_flagged)
def remove_flag(request, **kwargs):
    if kwargs['created'] and kwargs['flag'].flag == CommentFlag.SUGGEST_REMOVAL:
        comment = kwargs['comment']
        if is_admin_or_root(request.user) or request.user.is_authenticated and comment.user == request.user:
            comment.is_removed = True
            comment.save(update_fields=['is_removed'])
