import re

from django import forms
from blog.models import Blog
from django.utils.translation import ugettext_lazy as _
from utils.jinja2.globals import username_display
from account.models import User


def generate_username_link(matchobj):
    id = matchobj.group(1)
    try:
        user = User.objects.get(pk=id)
        return username_display(None, user)
    except:
        raise forms.ValidationError(_("User with id %d does not exist") % id)


class BlogEditForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'text', 'visible', 'hide_revisions']
        error_messages = {
        }
        help_texts = {
            'text': _('Markdown and MathJax are supported. Use $e^x$ for formulas.')
        }
        widgets = {
            'text': forms.Textarea(attrs={'class': 'markdown'})
        }

    def clean_text(self):
        text = self.cleaned_data["text"]
        return re.sub(r"\[user:(\d+)\]", generate_username_link, text)
