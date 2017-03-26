from rest_framework.views import APIView
from rest_framework.response import Response

from account.models import User
from django.contrib.auth import authenticate, login


class RegisterAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        username = request.data.get('username')
        password = request.data.get('password')
        user = User.objects.create(email=email, username=username)
        user.set_password(password)
        user.save()
        return Response({'username': user.username})


class LoginAPI(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        print(user)
        login(request, user)
        return Response({'username': user.username})
