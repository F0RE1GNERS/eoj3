from django.shortcuts import render, reverse
from random import randint


def home_view(request):
    return render(request, 'home.jinja2', context={'bg': '/static/image/bg/%d.jpg' % randint(1, 14),})


def forbidden_view(request):
    return render(request, 'error/403.jinja2')


def not_found_view(request):
    return render(request, 'error/404.jinja2')


def server_error_view(request):
    return render(request, 'error/500.jinja2')


def faq_view(request):
    return render(request, 'faq.jinja2')
