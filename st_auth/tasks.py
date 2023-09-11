import datetime
from http import HTTPStatus

import pytz
import requests.exceptions
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth.models import User

from .abstractapi_helper import check_signup_date_is_holiday, get_geolocation
from .models import Geolocation

logger = get_task_logger(__name__)


RETRYABLE_STATUS_CODES = (
    HTTPStatus.REQUEST_TIMEOUT.value,
    HTTPStatus.TOO_MANY_REQUESTS.value,
    HTTPStatus.BAD_GATEWAY.value,
    HTTPStatus.SERVICE_UNAVAILABLE.value,
    HTTPStatus.GATEWAY_TIMEOUT.value,
)


class RetryableHTTPStatusException(Exception):
    pass


@shared_task(
    name="st_auth.tasks.create_user_geolocation",
    bind=True,
    acks_late=True,
    max_retries=settings.CELERY_MAX_RETRIES,
    default_retry_delay=settings.CELERY_DELAY_BETWEEN_RETRIES,
    retry_backoff=settings.CELERY_RETRY_BACKOFF,
)
def create_user_geolocation(
    self, user_id: int, ip_address: str, signup_date_utc: str
) -> str:
    log_prefix = f"User_{user_id}@{ip_address}: "

    user = User.objects.filter(id=user_id).first()
    if not user:
        message = (
            log_prefix + "User cannot be found in DB! Skipping geolocation creation."
        )
        logger.warning(message)
        return message

    try:
        geolocation_response = get_geolocation(ip_address)

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        logger.warning(
            log_prefix
            + f"Request to geolocation api raised retryable exception: {exc}!"
        )
        raise self.retry(exc=exc)

    status_code = geolocation_response.status_code

    if status_code == HTTPStatus.OK.value:
        geolocation = geolocation_response.json()
        user_geolocation = Geolocation.objects.create(
            user=user, ip_address=ip_address, geolocation=geolocation
        )
        user_geolocation.save()

        update_is_signup_date_holiday.delay(user_geolocation.user_id, signup_date_utc)

        return log_prefix + "Successfully created geolocation information."

    elif status_code in RETRYABLE_STATUS_CODES:
        message = (
            log_prefix
            + f"Geolocation api returned a retryable status code - {status_code}."
        )
        logger.warning(message)
        raise self.retry(exc=RetryableHTTPStatusException(message))

    else:
        message = (
            log_prefix
            + f"Geolocation api response status code {status_code} is not good to retry."
        )
        logger.warning(message)
        return message


@shared_task(
    name="st_auth.tasks.update_is_signup_date_holiday",
    bind=True,
    acks_late=True,
    max_retries=settings.CELERY_MAX_RETRIES,
    default_retry_delay=settings.CELERY_DELAY_BETWEEN_RETRIES,
    retry_backoff=settings.CELERY_RETRY_BACKOFF,
)
def update_is_signup_date_holiday(
    self, geolocation_user_id: int, signup_date_utc
) -> str:
    # TODO: Refactor this and above task to use common code (DRY)
    log_prefix = f"Geolocation_{geolocation_user_id}: "

    user_geolocation = Geolocation.objects.filter(id=geolocation_user_id).first()
    if not user_geolocation:
        message = (
            log_prefix
            + "Geolocation cannot be found in DB! Skipping holiday column update."
        )
        logger.warning(message)
        return message

    try:
        country_code = user_geolocation.geolocation["country_code"]
        signup_date_user_country = convert_utc_to_user_time(
            signup_date_utc, user_geolocation.geolocation["timezone"]["name"]
        )
        holiday_response = check_signup_date_is_holiday(
            country_code, signup_date_user_country
        )

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        logger.warning(
            log_prefix + f"Request to holiday api raised retryable exception: {exc}!"
        )
        raise self.retry(exc=exc)

    status_code = holiday_response.status_code

    if status_code == HTTPStatus.OK.value:
        user_geolocation.signed_up_on_holiday = holiday_response.json() != []
        user_geolocation.save()

        return log_prefix + "Successfully updated holiday information."

    elif status_code in RETRYABLE_STATUS_CODES:
        message = (
            log_prefix
            + f"Holiday api returned a retryable status code - {status_code}."
        )
        logger.warning(message)
        raise self.retry(exc=RetryableHTTPStatusException(message))

    else:
        message = (
            log_prefix
            + f"Holiday api response status code {status_code} is not good to retry."
        )
        logger.warning(message)
        return message


def convert_utc_to_user_time(signup_date_utc: str, timezone_name: str):
    signup_date_utc = datetime.datetime.strptime(signup_date_utc, "%Y-%m-%d %H:%M:%S")
    signup_date_utc = signup_date_utc.replace(tzinfo=pytz.UTC)
    return signup_date_utc.astimezone(pytz.timezone(timezone_name))
