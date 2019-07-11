import json

from django.shortcuts import HttpResponseRedirect, reverse, HttpResponse
from django.views.generic.list import ListView, View
from django.db import transaction
from django.db.models import Q

from blog.models import Blog
from ..base_views import BaseBackstageMixin


class BlogList(BaseBackstageMixin, ListView):
    template_name = 'backstage/blog/blog.jinja2'
    paginate_by = 200
    context_object_name = 'blog_list'
    queryset = Blog.objects.select_related("author")


class BlogVisibleSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = Blog.objects.select_for_update().get(pk=pk)
            instance.visible = not instance.visible
            instance.save(update_fields=["visible"])
        return HttpResponse()


class BlogRecommendSwitch(BaseBackstageMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            instance = Blog.objects.select_for_update().get(pk=pk)
            instance.recommend = not instance.recommend
            instance.save(update_fields=["recommend"])
        return HttpResponse()
