from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
import pytz
import requests
from django.conf import settings
from django.contrib.auth.models import User

from ..models import Geolocation
from ..tasks import (
    RETRYABLE_STATUS_CODES,
    RetryableHTTPStatusException,
    convert_utc_to_user_time,
    create_user_geolocation,
    update_is_signup_date_holiday,
)


@pytest.mark.celery(result_backend="redis://")
@patch("st_auth.tasks.update_is_signup_date_holiday")
class TestCreateUserGeolocation:
    @patch("st_auth.tasks.Geolocation")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_task_completes_successfully(
        self,
        user_class_mock,
        get_geolocation_mock,
        geolocation_class_mock,
        update_is_signup_date_holiday_mock,
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "
        signup_date_utc = "2023-09-01 12:30:00"

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=HTTPStatus.OK.value)
        geolocation_response_data = {"dummy": "data"}
        response_mock.json.return_value = geolocation_response_data
        get_geolocation_mock.return_value = response_mock

        user_geolocation_mock = Mock(spec_set=Geolocation)
        geolocation_class_mock.objects.create.return_value = user_geolocation_mock

        result = create_user_geolocation.apply(
            args=(user_id, ip_address, signup_date_utc)
        ).get()

        user_class_mock.objects.filter.assert_called_once_with(id=user_id)
        get_geolocation_mock.assert_called_once_with(ip_address)
        geolocation_class_mock.objects.create.assert_called_once_with(
            user=user_mock, ip_address=ip_address, geolocation=geolocation_response_data
        )
        user_geolocation_mock.save.assert_called_once_with()
        update_is_signup_date_holiday_mock.delay.assert_called_once_with(
            user_geolocation_mock.id, signup_date_utc
        )
        assert result == log_prefix + "Successfully created geolocation information."

    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.User")
    def test_user_not_found(
        self, user_class_mock, logger_mock, update_is_signup_date_holiday_mock
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "
        signup_date_utc = "2023-09-01 12:30:00"

        user_class_mock.objects.filter.return_value.first.return_value = None

        result = create_user_geolocation.apply(
            args=(user_id, ip_address, signup_date_utc)
        ).get()

        message = (
            log_prefix + "User cannot be found in DB! Skipping geolocation creation."
        )
        logger_mock.warning.assert_called_once_with(message)
        update_is_signup_date_holiday_mock.delay.assert_not_called()
        assert result == message

    @pytest.mark.parametrize("status_code", RETRYABLE_STATUS_CODES)
    @patch("st_auth.tasks.logger")
    @patch("st_auth.tasks.get_geolocation")
    @patch("st_auth.tasks.User")
    def test_geolocation_api_returns_retryable_status_code(
        self,
        user_class_mock,
        get_geolocation_mock,
        logger_mock,
        update_is_signup_date_holiday_mock,
        status_code,
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "
        signup_date_utc = "2023-09-01 12:30:00"

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=status_code)
        get_geolocation_mock.return_value = response_mock

        with pytest.raises(RetryableHTTPStatusException) as exc:
            _ = create_user_geolocation.apply(
                args=(user_id, ip_address, signup_date_utc)
            ).get()

        assert (
            user_class_mock.objects.filter.call_count == settings.CELERY_MAX_RETRIES + 1
        )
        assert get_geolocation_mock.call_count == settings.CELERY_MAX_RETRIES + 1
        assert logger_mock.warning.call_count == settings.CELERY_MAX_RETRIES + 1
        update_is_signup_date_holiday_mock.delay.assert_not_called()
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
        self,
        user_class_mock,
        get_geolocation_mock,
        logger_mock,
        update_is_signup_date_holiday_mock,
        status_code,
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        log_prefix = f"User_{user_id}@{ip_address}: "
        signup_date_utc = "2023-09-01 12:30:00"

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        response_mock = Mock(spec=requests.Response, status_code=status_code)
        get_geolocation_mock.return_value = response_mock

        result = create_user_geolocation.apply(
            args=(user_id, ip_address, signup_date_utc)
        ).get()

        assert user_class_mock.objects.filter.call_count == 1
        assert get_geolocation_mock.call_count == 1
        assert logger_mock.warning.call_count == 1
        update_is_signup_date_holiday_mock.delay.assert_not_called()
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
        self,
        user_class_mock,
        get_geolocation_mock,
        logger_mock,
        update_is_signup_date_holiday_mock,
        request_exception,
    ):
        user_id = 1
        ip_address = "127.0.0.1"
        signup_date_utc = "2023-09-01 12:30:00"

        user_mock = Mock(spec=User, id=user_id)
        user_class_mock.objects.filter.return_value.first.return_value = user_mock

        get_geolocation_mock.side_effect = request_exception

        with pytest.raises(request_exception.__class__) as exc:
            _ = create_user_geolocation.apply(
                args=(user_id, ip_address, signup_date_utc)
            ).get()

        assert (
            user_class_mock.objects.filter.call_count == settings.CELERY_MAX_RETRIES + 1
        )
        assert get_geolocation_mock.call_count == settings.CELERY_MAX_RETRIES + 1
        assert logger_mock.warning.call_count == settings.CELERY_MAX_RETRIES + 1
        update_is_signup_date_holiday_mock.delay.assert_not_called()
        assert str(exc.value) == str(request_exception)


@pytest.mark.celery(result_backend="redis://")
class TestUpdateIsSignupDateHoliday:
    @patch("st_auth.tasks.Geolocation")
    @patch("st_auth.tasks.check_signup_date_is_holiday")
    def test_task_completes_successfully(
        self, check_signup_date_is_holiday_mock, geolocation_class_mock
    ):
        user_geolocation_id = 1
        log_prefix = f"Geolocation_{user_geolocation_id}: "
        signup_date_utc = "2023-09-01 12:30:00"
        country_code = "TR"
        timezone_name = "Europe/Istanbul"

        user_geolocation_mock = Mock(spec_set=Geolocation, id=user_geolocation_id)
        user_geolocation_mock.geolocation = {
            "country_code": country_code,
            "timezone": {"name": timezone_name},
        }
        geolocation_class_mock.objects.filter.return_value.first.return_value = (
            user_geolocation_mock
        )

        response_mock = Mock(spec=requests.Response, status_code=HTTPStatus.OK.value)
        holiday_response_data = [{"dummy": "holiday"}]
        response_mock.json.return_value = holiday_response_data
        check_signup_date_is_holiday_mock.return_value = response_mock

        result = update_is_signup_date_holiday.apply(
            args=(user_geolocation_id, signup_date_utc)
        ).get()

        geolocation_class_mock.objects.filter.assert_called_once_with(
            id=user_geolocation_id
        )
        signup_date_user_country = convert_utc_to_user_time(
            signup_date_utc, timezone_name
        )
        check_signup_date_is_holiday_mock.assert_called_once_with(
            country_code, signup_date_user_country
        )
        assert user_geolocation_mock.signed_up_on_holiday is True
        user_geolocation_mock.save.assert_called_once_with()
        assert result == log_prefix + "Successfully updated holiday information."


class TestConvertUTCToUserTime:
    def test_correct_format(self):
        result = convert_utc_to_user_time(
            signup_date_utc="2023-09-30 22:30:00", timezone_name="Europe/Istanbul"
        )
        assert (result.year, result.month, result.day) == (2023, 10, 1)
        assert (result.hour, result.minute, result.second) == (1, 30, 0)

    def test_wrong_format(self):
        with pytest.raises(ValueError):
            _ = convert_utc_to_user_time(
                signup_date_utc="30-09-2023 22:30:00", timezone_name="Europe/Istanbul"
            )

    def test_wrong_timezone(self):
        with pytest.raises(pytz.exceptions.UnknownTimeZoneError):
            _ = convert_utc_to_user_time(
                signup_date_utc="2023-09-30 22:30:00", timezone_name="DUMMY_TIMEZONE"
            )
