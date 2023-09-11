from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

from ..serializers import SignUpSerializer


@pytest.fixture
def db_user_1():
    return User.objects.create_user(username="user1@domain.com", password="password")


@pytest.mark.django_db
@patch(
    "st_auth.serializers.validate_email_with_api",
    return_value={"success": "user1@domain.com"},
)
class TestSignUpSerializer:
    def test_new_user(self, validate_email_mock):
        serializer = SignUpSerializer(
            data={"email": "user1@domain.com", "password": "password"}
        )

        assert serializer.is_valid()

        user = serializer.save()
        assert user.username == "user1@domain.com"

    def test_existing_user(self, validate_email_mock, db_user_1):
        serializer = SignUpSerializer(
            data={"email": "user1@domain.com", "password": "password"}
        )

        assert serializer.is_valid()

        with pytest.raises(IntegrityError):
            _ = serializer.save()
