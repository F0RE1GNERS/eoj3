from django.shortcuts import render
from .forms import RegisterForm


def login_view(request):
    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        pass
    else:
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})
