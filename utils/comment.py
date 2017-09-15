from django import forms
from django.dispatch import receiver
from django.template import loader
from django.contrib.auth.decorators import login_required
from django_comments.views.comments import post_comment
from django_comments.models import CommentFlag
from django_comments.signals import comment_was_flagged, comment_was_posted
from django_comments_xtd.forms import XtdCommentForm
from django_comments_xtd.models import XtdComment
from notifications.signals import notify

from problem.models import Problem
from contest.models import Contest
from account.permissions import is_admin_or_root
from utils.permission import has_permission_for_contest_management
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


@login_required
def login_required_post_comment(*args, **kwargs):
    return post_comment(*args, **kwargs)


@receiver(comment_was_flagged)
def remove_flag(request, **kwargs):
    if kwargs['created'] and kwargs['flag'].flag == CommentFlag.SUGGEST_REMOVAL:
        comment = kwargs['comment']
        if is_admin_or_root(request.user) or request.user.is_authenticated and comment.user == request.user:
            comment.is_removed = True
            comment.save(update_fields=['is_removed'])


@receiver(comment_was_posted)
def send_notification(request, **kwargs):
    def get_parent_user(comment):
        return XtdComment.objects.get(pk=comment['parent_id']).user

    comment = kwargs['comment']
    if comment['content_type'].name in ('blog', 'problem', 'contest'):
        recipient = None
        target = None
        verb = 'replied on'
        if comment['content_type'].name == 'blog':
            target = comment['content_object']
            recipient = target.author
            if comment['parent_id']:
                recipient = get_parent_user(comment)
        elif comment['content_type'].name == 'contest':
            target = contest = comment['content_object']
            if comment['parent_id']:
                recipient = get_parent_user(comment)
                verb = 'replied in'
            elif has_permission_for_contest_management(comment.user, contest):
                recipient = list(map(lambda x: x.user, contest.contestparticipant_set.all()))
                verb = 'posted a notification in'
            else:
                recipient = contest.managers.all()
                verb = 'asked a question in'
        elif comment['content_type'].name == 'problem':
            if comment['parent_id']:
                target = comment['content_object']
                recipient = get_parent_user(comment)
            else:
                return

        level = 'info'
        if comment['content_type'].name == 'contest':
            level = 'warning'

        if recipient and recipient != comment['user']:
            notify.send(sender=comment['user'],
                        recipient=recipient,
                        verb=verb,
                        level=level,
                        target=target)
