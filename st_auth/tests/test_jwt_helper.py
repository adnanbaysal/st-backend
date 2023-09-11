import pytest
from django.contrib.auth.models import User

from ..jwt_helper import get_tokens_for_user


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
