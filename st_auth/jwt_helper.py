from typing import Dict

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user: User) -> Dict[str, str]:
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
