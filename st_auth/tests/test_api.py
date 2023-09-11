from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.exceptions import ErrorDetail

from ..api import _get_ip_address_from_request, signup


@pytest.fixture
def db_user_1():
    return User.objects.create_user(username="user1@domain.com", password="password")


@pytest.mark.django_db
@patch("st_auth.serializers.validate_email_with_api")
class TestSignupView:
    factory = RequestFactory()

    @patch("st_auth.api.create_user_geolocation")
    def test_signup_new_user(self, create_user_geolocation_mock, validate_email_mock):
        validate_email_mock.return_value = {"success": "user1@domain.com"}
        url = reverse("auth_signup")
        request = self.factory.post(
            url, data={"email": "user1@domain.com", "password": "password"}
        )
        request.user = AnonymousUser()

        response = signup(request)

        assert response.status_code == HTTPStatus.OK.value

        assert "refresh" in response.data
        assert "access" in response.data

        validate_email_mock.assert_called_once_with("user1@domain.com")
        create_user_geolocation_mock.delay.assert_called_once()

    @pytest.mark.usefixtures("db_user_1")
    def test_signup_existing_user(self, validate_email_mock):
        validate_email_mock.return_value = {"success": "user1@domain.com"}
        url = reverse("auth_signup")
        request = self.factory.post(
            url, data={"email": "user1@domain.com", "password": "password"}
        )

        request.user = AnonymousUser()

        response = signup(request)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert response.data == {"error": "user_already_exists"}

    def test_email_validation_fails_with_did_you_mean(self, validate_email_mock):
        validate_email_mock.return_value = {"did_you_mean": "user123@domain.com"}
        url = reverse("auth_signup")
        request = self.factory.post(
            url, data={"email": "user1@domain.com", "password": "password"}
        )

        request.user = AnonymousUser()

        response = signup(request)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert response.data == {
            "email": {
                "did_you_mean": ErrorDetail(string="user123@domain.com", code="invalid")
            }
        }

    @patch("st_auth.api.logger")
    def test_ip_address_cannot_be_determined(self, logger_mock, validate_email_mock):
        validate_email_mock.return_value = {"success": "user1@domain.com"}
        url = reverse("auth_signup")
        request = self.factory.post(
            url, data={"email": "user1@domain.com", "password": "password"}
        )

        request.user = AnonymousUser()
        request.META["REMOTE_ADDR"] = None

        response = signup(request)

        assert response.status_code == HTTPStatus.OK.value
        logger_mock.warning.assert_called_once()


class TestGetIpAddressFromRequest:
    def test_ip_from_x_forwarded_for(self):
        request = Mock()
        request.headers = {"X-Forwarded-For": "1.1.1.1,2.2.2.2,3.3.3.3"}

        result = _get_ip_address_from_request(request)
        assert result == "1.1.1.1"

    def test_ip_from_remote_addr(self):
        request = Mock()
        request.headers = {}
        request.META = {"REMOTE_ADDR": "3.3.3.3"}

        result = _get_ip_address_from_request(request)
        assert result == "3.3.3.3"
