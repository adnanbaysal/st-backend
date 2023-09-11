from django.urls import path

from .api import login, signup

urlpatterns = [
    path("signup", signup, name="auth_signup"),
    path("login", login, name="auth_login"),
]
