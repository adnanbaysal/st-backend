from django.contrib.auth.models import User
from rest_framework import serializers

from .abstractapi_helper import validate_email as validate_email_with_api


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

    @staticmethod
    def validate_email(email):
        validation_response = validate_email_with_api(email)

        if validation_response != {"success": email}:
            raise serializers.ValidationError(validation_response)

        return email


class TokenResponseSerializer(serializers.Serializer):  # noqa
    email = serializers.CharField()
    token = serializers.CharField()
