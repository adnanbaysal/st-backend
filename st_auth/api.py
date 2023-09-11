import datetime
from logging import getLogger

from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .jwt_helper import get_tokens_for_user
from .serializers import (
    GeolocationSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    SignUpSerializer,
    TokenResponseSerializer,
    UserSerializer,
)
from .tasks import create_user_geolocation

logger = getLogger(__name__)


@extend_schema(
    request=SignUpSerializer,
    responses={
        status.HTTP_200_OK: TokenResponseSerializer,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Bad request"),
        status.HTTP_502_BAD_GATEWAY: OpenApiResponse(description="Bad gateway"),
    },
)
@api_view(["POST"])
def signup(request: Request):
    if User.objects.filter(username=request.data.get("email")).exists():
        return Response(
            {"error": "user_already_exists"}, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = SignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()

    user_ip = _get_ip_address_from_request(request)
    if user_ip:
        now = datetime.datetime.utcnow()
        signup_date_utc = now.strftime("%Y-%m-%d %H:%M:%S")
        create_user_geolocation.delay(user.id, user_ip, signup_date_utc)
    else:
        logger.warning(
            f"Empty IP address for user {user.id}! Cannot create geolocation data."
        )

    tokens = get_tokens_for_user(user)

    return Response(tokens)


def _get_ip_address_from_request(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]

    return request.META.get("REMOTE_ADDR", "")


@extend_schema(
    request=LoginSerializer,
    responses={
        status.HTTP_200_OK: LoginResponseSerializer,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Bad request"),
        status.HTTP_502_BAD_GATEWAY: OpenApiResponse(description="Bad gateway"),
    },
)
@api_view(["POST"])
def login(request: Request):
    if not User.objects.filter(username=request.data.get("email")).exists():
        return Response(
            {"error": "user_does_not_exists"}, status=status.HTTP_400_BAD_REQUEST
        )

    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data
    tokens = get_tokens_for_user(user)

    geolocation = None
    if hasattr(user, "geolocation") and user.geolocation:
        geolocation = GeolocationSerializer(user.geolocation).data

    return Response(
        {
            "user": UserSerializer(user).data,
            "geolocation": geolocation,
            "tokens": tokens,
        }
    )
