from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from .abstractapi_helper import validate_email as validate_email_with_api
from .models import Geolocation


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
    access = serializers.CharField()
    refresh = serializers.CharField()


class GeolocationSerializer(serializers.ModelSerializer):
    ip_address = serializers.CharField()
    geolocation = serializers.DictField()
    signed_up_on_holiday = serializers.BooleanField()

    class Meta:
        model = Geolocation
        fields = ("user_id", "ip_address", "geolocation", "signed_up_on_holiday")


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = User
        fields = ("id", "username")


class LoginSerializer(serializers.Serializer):  # noqa
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        data["username"] = data["email"]
        user = authenticate(**data)
        if user:
            return user
        raise serializers.ValidationError("Incorrect Credentials")


class LoginResponseSerializer(serializers.Serializer):  # noqa
    user = UserSerializer(read_only=True)
    geolocation = GeolocationSerializer(read_only=True, required=False)
    tokens = TokenResponseSerializer()
