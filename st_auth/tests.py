from http import HTTPStatus
from http.client import HTTPException
from unittest.mock import Mock, patch

import pytest
import requests
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.db.utils import IntegrityError
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail

from .abstractapi_helper import get_geolocation, validate_email
from .api import _get_ip_address_from_request, signup  # noqa
from .jwt_helper import get_tokens_for_user
from .models import Geolocation
from .serializers import SignUpSerializer
from .tasks import (
    RETRYABLE_STATUS_CODES,
    RetryableHTTPStatusException,
    create_user_geolocation,
)


@pytest.fixture
def db_user_1():
    return User.objects.create_user(username="user1@domain.com", password="password")


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


@patch("st_auth.abstractapi_helper.requests")
class TestValidateEmail:
    def test_validation_succeeds(self, requests_mock):
        email = "fredymercury@gmail.com"
        requests_mock.get.return_value.json.return_value = {
            "email": "fredymercury@gmail.com",
            "autocorrect": "",
            "deliverability": "DELIVERABLE",
            "quality_score": "0.95",
            "is_valid_format": {"value": True, "text": "TRUE"},
        }
        url = f"{settings.ABSTRACT_API_EMAIL_URL}?api_key={settings.ABSTRACT_API_EMAIL_KEY}&email={email}"

        result = validate_email(email)
        requests_mock.get.assert_called_once_with(url)
        assert result == {"success": email}

    def test_request_raises_exception(self, requests_mock):
        email = "fredymercury@gmail.com"
        error_message = "500: API call failed"
        requests_mock.get.side_effect = HTTPException(error_message)
        with pytest.raises(serializers.ValidationError) as error:
            _ = validate_email(email)

        assert error.value.detail == {
            "validation_error": f"Gateway call `GET {settings.ABSTRACT_API_EMAIL_URL}` failed: {error_message}"
        }

    def test_response_data_invalid(self, requests_mock):
        email = "fredymercury@gmail.com"
        return_dict = {
            "email": "fredymercury@gmail.com",
            "autocorrect": "",
            "deliverability": "DELIVERABLE",
            "quality_score": "0.95",
            "is_valid_format": {},
        }
        requests_mock.get.return_value.json.return_value = return_dict

        with pytest.raises(serializers.ValidationError) as error:
            _ = validate_email(email)

        assert error.value.detail == {
            "validation_error": f"Bad response from gateway {settings.ABSTRACT_API_EMAIL_URL}:\n{return_dict}"
        }

    def test_invalid_email_format(self, requests_mock):
        email = "fredymercury"
        requests_mock.get.return_value.json.return_value = {
            "email": "fredymercury",
            "autocorrect": "",
            "deliverability": "UNDELIVERABLE",
            "quality_score": "0.00",
            "is_valid_format": {"value": False, "text": "TRUE"},
        }

        result = validate_email(email)
        assert result == {"validation_error": "invalid_email_format"}

    def test_auto_correct_suggested(self, requests_mock):
        email = "fredymercury@gmal.com"
        requests_mock.get.return_value.json.return_value = {
            "email": "fredymercury@gmal.com",
            "autocorrect": "fredymercury@gmail.com",
            "deliverability": "UNDELIVERABLE",
            "quality_score": "0.00",
            "is_valid_format": {"value": True, "text": "TRUE"},
        }

        result = validate_email(email)
        assert result == {"did_you_mean": "fredymercury@gmail.com"}

    def test_unusable_email(self, requests_mock):
        email = "fredymercury@gmail.com"
        requests_mock.get.return_value.json.return_value = {
            "email": "fredymercury@gmail.com",
            "autocorrect": "",
            "deliverability": "UNDELIVERABLE",
            "quality_score": "0.00",
            "is_valid_format": {"value": True, "text": "TRUE"},
        }

        result = validate_email(email)
        assert result == {"validation_error": "unusable_email"}


@patch("st_auth.abstractapi_helper.requests")
def test_get_geolocation(requests_mock):
    get_geolocation("1.1.1.1")
    assert "1.1.1.1" in requests_mock.get.call_args_list[0].args[0]


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


@pytest.mark.celery(result_backend="redis://")
class TestCreateUserGeolocation:
    @patch("st_auth.tasks.Geolocation")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_task_completes_successfully(
        self, user_class_mock, get_geolocation_mock, geolocation_class_mock
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=HTTPStatus.OK.value)
        geolocation_response_data = {"dummy": "data"}
        response_mock.json.return_value = geolocation_response_data
        get_geolocation_mock.return_value = response_mock

        user_geolocation_mock = Mock(spec_set=Geolocation)
        geolocation_class_mock.objects.create.return_value = user_geolocation_mock

        result = create_user_geolocation.apply(args=(user_id, ip_address)).get()

        user_class_mock.objects.filter.assert_called_once_with(id=user_id)
        get_geolocation_mock.assert_called_once_with(ip_address)
        geolocation_class_mock.objects.create.assert_called_once_with(
            user=user_mock, ip_address=ip_address, geolocation=geolocation_response_data
        )
        user_geolocation_mock.save.assert_called_once_with()
        assert result == log_prefix + "Successfully created geolocation information."

    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.User")
    def test_user_not_found(self, user_class_mock, logger_mock):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "

        user_class_mock.objects.filter.return_value.first.return_value = None

        result = create_user_geolocation.apply(args=(user_id, ip_address)).get()

        message = (
            log_prefix + "User cannot be found in DB! Skipping geolocation creation."
        )
        logger_mock.warning.assert_called_once_with(message)
        assert result == message

    @pytest.mark.parametrize("status_code", RETRYABLE_STATUS_CODES)
    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_geolocation_api_returns_retryable_status_code(
        self, user_class_mock, get_geolocation_mock, logger_mock, status_code
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=status_code)
        get_geolocation_mock.return_value = response_mock

        with pytest.raises(RetryableHTTPStatusException) as exc:
            _ = create_user_geolocation.apply(args=(user_id, ip_address)).get()

        assert (
            user_class_mock.objects.filter.call_count == settings.CELERY_MAX_RETRIES + 1
        )
        assert get_geolocation_mock.call_count == settings.CELERY_MAX_RETRIES + 1
        assert logger_mock.warning.call_count == settings.CELERY_MAX_RETRIES + 1
        assert (
            str(exc.value)
            == log_prefix
            + f"Geolocation api returned a retryable status code - {status_code}."
        )

    @pytest.mark.parametrize("status_code", [400, 401, 402, 403, 404, 405])
    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_geolocation_api_returns_non_retryable_status_code(
        self, user_class_mock, get_geolocation_mock, logger_mock, status_code
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=status_code)
        get_geolocation_mock.return_value = response_mock

        result = create_user_geolocation.apply(args=(user_id, ip_address)).get()

        assert user_class_mock.objects.filter.call_count == 1
        assert get_geolocation_mock.call_count == 1
        assert logger_mock.warning.call_count == 1
        assert (
            result
            == log_prefix
            + f"Geolocation api response status code {status_code} is not good to retry."
        )

    @pytest.mark.parametrize(
        "request_exception",
        [
            requests.exceptions.Timeout("timeout"),
            requests.exceptions.ConnectionError("connection_error"),
        ],
    )
    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_geolocation_api_raises_retryable_exception(
        self, user_class_mock, get_geolocation_mock, logger_mock, request_exception
    ):
        user_id = 1
        ip_address = "127.0.0.1"

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        get_geolocation_mock.side_effect = request_exception

        with pytest.raises(request_exception.__class__) as exc:
            _ = create_user_geolocation.apply(args=(user_id, ip_address)).get()

        assert (
            user_class_mock.objects.filter.call_count == settings.CELERY_MAX_RETRIES + 1
        )
        assert get_geolocation_mock.call_count == settings.CELERY_MAX_RETRIES + 1
        assert logger_mock.warning.call_count == settings.CELERY_MAX_RETRIES + 1
        assert str(exc.value) == str(request_exception)
