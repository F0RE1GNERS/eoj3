from django.shortcuts import render
from .forms import RegisterForm


def login_view(request):
    if request.method == 'POST':
        pass
    else:
        form = RegisterForm()
        return render(request, 'login.html', {'form': form})


def register_view(request):
    return render(request, 'register.html')
