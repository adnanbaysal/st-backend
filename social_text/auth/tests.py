# from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

from .jwt_helper import get_tokens_for_user
from .serializers import SignUpSerializer

# from django.test import TestCase
# from django.urls import reverse


@pytest.mark.django_db
class TestGetTokensForUser:
    @pytest.fixture
    def user(self):
        return User(username="test_user", password="12345")

    def test_user_exists(self, user):
        tokens = get_tokens_for_user(user)

        assert "access" in tokens
        assert "refresh" in tokens

    def test_non_user_has_no_id_field(self):
        non_user = "non_user"

        with pytest.raises(AttributeError):
            _ = get_tokens_for_user(non_user)


@pytest.mark.django_db
class TestSignUpSerializer:
    @pytest.fixture
    def user_1(self):
        return User.objects.create_user(
            username="email@domain.com", password="password"
        )

    def test_new_user(self):
        serializer = SignUpSerializer(
            data={"email": "email@domain.com", "password": "password"}
        )

        assert serializer.is_valid()

        user = serializer.save()
        assert user.username == "email@domain.com"

    def test_existing_user(self, user_1):
        serializer = SignUpSerializer(
            data={"email": "email@domain.com", "password": "password"}
        )

        assert serializer.is_valid()

        with pytest.raises(IntegrityError):
            _ = serializer.save()


# @pytest.mark.django_db
# class TestSignupView(TestCase):
#     def test_signup_new_user(self):
#         url = reverse("auth_signup")
#         response = self.client.post(url, data={"email": "email@domain.com", "password": "password"})
#
#         assert response.status_code == HTTPStatus.OK
#
#         json_data = response.json()
#         assert "refresh" in json_data
#         assert "access" in json_data
