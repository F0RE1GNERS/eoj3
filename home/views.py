from django.shortcuts import render, reverse
from random import randint
from utils.models import get_site_settings


def home_view(request):
    site_settings = get_site_settings()
    broadcast = site_settings.broadcast_message
    link = site_settings.broadcast_link
    return render(request, 'home.jinja2', context={'bg': '/static/image/bg/%d.jpg' % randint(1, 14),
                                                   'broadcast_message': broadcast,
                                                   'broadcast_link': link})


def forbidden_view(request):
    return render(request, 'error/403.jinja2')


def not_found_view(request):
    return render(request, 'error/404.jinja2')


def server_error_view(request):
    return render(request, 'error/500.jinja2')


def faq_view(request):
    return render(request, 'faq.jinja2')
