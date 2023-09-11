import datetime
from http.client import HTTPException
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework import serializers

from ..abstractapi_helper import (
    check_signup_date_is_holiday,
    get_geolocation,
    validate_email,
)


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


@patch("st_auth.abstractapi_helper.requests")
def test_check_signup_date_is_holiday(requests_mock):
    date_ = datetime.datetime(2023, 9, 23)
    check_signup_date_is_holiday("US", date_)
    request_call_arg = requests_mock.get.call_args_list[0].args[0]

    assert "country=US" in request_call_arg
    assert "year=2023" in request_call_arg
    assert "month=9" in request_call_arg
    assert "day=23" in request_call_arg
