from django import forms
from blog.models import Blog


class BlogEditForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'text', 'visible']
        error_messages = {
        }
