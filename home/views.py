from django.shortcuts import render, reverse
from random import randint
from blog.models import Blog
from django.views.generic import TemplateView
from submission.statistics import get_accept_problem_count
from utils.models import site_settings_get

def home_view(request):
    if request.user.is_authenticated:
        return render(request, 'home_logged_in.jinja2', context={'solved': get_accept_problem_count(request.user.pk),
                                                                 'blog_list': Blog.objects.filter(visible=True)[:15],
                                                                 'bulletin': site_settings_get('BULLETIN', '')})
    else:
        return render(request, 'home.jinja2', context={'bg': '/static/image/bg/%d.jpg' % randint(1, 14),})


def forbidden_view(request):
    return render(request, 'error/403.jinja2')


def not_found_view(request):
    return render(request, 'error/404.jinja2')


def server_error_view(request):
    return render(request, 'error/500.jinja2')


def faq_view(request):
    return render(request, 'faq.jinja2')


class TestView(TemplateView):
    template_name = 'test.jinja2'
