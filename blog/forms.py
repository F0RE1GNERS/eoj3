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
        raise forms.ValidationError("用户 ID %d 不存在" % id)


class BlogEditForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'text', 'visible', 'hide_revisions']
        error_messages = {
        }
        help_texts = {
            'text': "支持 Markdown 和 MathJax，使用 $e^x$ 来写公式。"
        }
        widgets = {
            'text': forms.Textarea(attrs={'class': 'markdown'})
        }

    def clean_text(self):
        text = self.cleaned_data["text"]
        return re.sub(r"\[user:(\d+)\]", generate_username_link, text)
