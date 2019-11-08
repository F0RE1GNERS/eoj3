from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from account.models import User


class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = (
      "username", "school", "name",
      "student_id", "avatar", "score",
    )


class UserView(RetrieveAPIView):
  queryset = User.objects.all()
  serializer_class = UserSerializer
