import requests
from django.conf import settings
from requests import Response
from rest_framework import serializers, status


def _analyze_email_response(response_data: dict) -> dict:
    if not response_data["is_valid_format"]["value"]:
        return {"validation_error": "invalid_email_format"}

    auto_correct = response_data["autocorrect"]
    email = response_data["email"]

    if auto_correct != "" and auto_correct != email:
        return {"did_you_mean": auto_correct}

    if response_data["deliverability"] == "DELIVERABLE":
        return {"success": email}

    return {"validation_error": "unusable_email"}


def validate_email(email: str) -> dict:
    try:
        response = requests.get(
            f"{settings.ABSTRACT_API_EMAIL_URL}?api_key={settings.ABSTRACT_API_EMAIL_KEY}&email={email}"
        )
    except Exception as e:
        raise serializers.ValidationError(
            {
                "validation_error": f"Gateway call `GET {settings.ABSTRACT_API_EMAIL_URL}` failed: {str(e)}"
            },
            status.HTTP_502_BAD_GATEWAY,
        )

    try:
        return _analyze_email_response(response.json())
    except (KeyError, TypeError):
        raise serializers.ValidationError(
            {
                "validation_error": f"Bad response from gateway {settings.ABSTRACT_API_EMAIL_URL}:\n{response.json()}"
            },
            status.HTTP_502_BAD_GATEWAY,
        )


def get_geolocation(ip_address: str) -> Response:
    return requests.get(
        f"{settings.ABSTRACT_API_GEOLOCATION_URL}?api_key={settings.ABSTRACT_API_GEOLOCATION_KEY}&ip_address="
        f"{ip_address}"
    )
