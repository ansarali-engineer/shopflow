"""Authentication URL routes."""
from django.urls import path
from apps.authentication.views import (
    register, login, refresh_token, me, change_password_view,
)

urlpatterns = [
    path("register/", register),
    path("login/", login),
    path("refresh/", refresh_token),
    path("me/", me),
    path("change-password/", change_password_view),
]
