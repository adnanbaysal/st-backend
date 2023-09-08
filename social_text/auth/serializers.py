from django.contrib.auth.models import User
from rest_framework import serializers


class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
        )
        extra_kwargs = {"password": {"write_only": True}}

    @staticmethod
    def create(validated_data):
        return User.objects.create_user(
            username=validated_data["email"],
            password=validated_data["password"],
        )


class TokenResponseSerializer(serializers.Serializer):  # noqa
    email = serializers.CharField()
    token = serializers.CharField()
