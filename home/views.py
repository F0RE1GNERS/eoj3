from django.shortcuts import render, reverse
from random import randint

def home_view(request):
    return render(request, 'home.jinja2', context={'bg': reverse('static', kwargs={'path': 'image/bg/%d.jpg' % randint(1, 14)})})
