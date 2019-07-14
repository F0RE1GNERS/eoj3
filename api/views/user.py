from rest_framework.generics import RetrieveAPIView

from account.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username", "email", "school", "name",
            "student_id", "avatar", "score",
        )


class UserView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

