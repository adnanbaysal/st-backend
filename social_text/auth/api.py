from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .jwt_helper import get_tokens_for_user
from .serializers import SignUpSerializer, TokenResponseSerializer


@extend_schema(
    request=SignUpSerializer,
    responses={
        status.HTTP_200_OK: TokenResponseSerializer,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description='{"error": "user_already_exists"}'
        ),
    },
)
@api_view(["POST"])
def signup(request):
    serializer = SignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if User.objects.filter(username=request.data.get("email")).exists():
        return Response(
            {"error": "user_already_exists"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.save()
    tokens = get_tokens_for_user(user)

    return Response(tokens)
