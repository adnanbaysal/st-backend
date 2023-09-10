from django.urls import path

from .api import signup

urlpatterns = [
    path("signup", signup, name="auth_signup"),
]
