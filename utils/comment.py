from django import forms
from django.dispatch import receiver
from django.template import loader
from django_comments.models import CommentFlag
from django_comments.signals import comment_was_flagged, comment_was_posted
from django_comments_xtd.forms import XtdCommentForm
from django_comments_xtd.models import XtdComment
from notifications.signals import notify

from account.permissions import is_admin_or_root
from blog.models import Blog


class CommentForm(XtdCommentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['email'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['url'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['honeypot'] = forms.CharField(widget=forms.HiddenInput)
        self.fields['followup'] = forms.BooleanField(widget=forms.HiddenInput)
        self.fields['comment'].widget = forms.Textarea(attrs={'class': 'markdown'})
        self.fields['comment'].label = ''


@receiver(comment_was_flagged)
def remove_flag(request, **kwargs):
    if kwargs['created'] and kwargs['flag'].flag == CommentFlag.SUGGEST_REMOVAL:
        comment = kwargs['comment']
        if is_admin_or_root(request.user) or request.user.is_authenticated and comment.user == request.user:
            comment.is_removed = True
            comment.save(update_fields=['is_removed'])


@receiver(comment_was_posted)
def send_notification(request, **kwargs):
    comment = kwargs['comment']
    if comment['content_type'].name in ('blog', 'problem'):
        if comment['parent_id']:
            recipient = XtdComment.objects.get(pk=comment['parent_id']).user
        elif comment['content_type'].name == 'blog':
            recipient = Blog.objects.get(pk=comment['object_pk']).author
        else:
            return
        if recipient != comment['user']:
            notify.send(sender=comment['user'],
                        recipient=recipient,
                        verb='comment_reply',
                        action_object=comment['xtd_comment'],
                        description=loader.render_to_string('notification/comment_reply.jinja2',
                                                            context={
                                                                'url': request.POST.get('next', None),
                                                                'comment': comment['comment'],
                                                                'user': comment['user']
                                                            }))
