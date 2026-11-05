"""
JWT authentication backend for ShopFlow.

Uses raw SQL to fetch user data and wraps it in a ShopFlowUser
dataclass that DRF can use for request.user.
"""
import logging
from dataclasses import dataclass
from typing import Any

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from repositories.user_repository import get_user_by_id

logger = logging.getLogger("shopflow.auth")


@dataclass
class ShopFlowUser:
    """Lightweight user object for request.user without Django ORM."""
    id: int
    email: str
    role: str
    first_name: str = ""
    last_name: str = ""
    status: str = "active"

    @property
    def pk(self) -> int:
        """Expose the primary-key alias expected by Django and DRF."""
        return self.id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class ShopFlowJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that loads user data via raw SQL
    instead of Django's ORM User model.

    Overrides `authenticate` to return None (anonymous) instead of
    raising AuthenticationFailed when the token is missing, expired or
    invalid.  This lets AllowAny / public views work even when the
    client still sends an old or expired token in the header.
    DRF's permission layer is responsible for rejecting unauthenticated
    requests on protected endpoints.
    """

    def authenticate(self, request):
        """Return (user, token) or None — never raise."""
        try:
            return super().authenticate(request)
        except Exception:
            # Expired, malformed, or revoked token → treat as anonymous.
            # Protected views will still reject the request via their
            # permission classes (IsAuthenticated etc.).
            return None

    def get_user(self, validated_token: AccessToken) -> ShopFlowUser | None:
        try:
            user_id = validated_token["user_id"]
        except KeyError:
            logger.warning("JWT token missing user_id claim")
            return None

        user_row = get_user_by_id(user_id)
        if user_row is None:
            logger.warning("User %s not found for valid JWT", user_id)
            return None

        if user_row.get("status") != "active":
            logger.warning("Inactive user %s attempted auth", user_id)
            return None

        return ShopFlowUser(
            id=user_row["id"],
            email=user_row["email"],
            role=user_row["role"],
            first_name=user_row.get("first_name", ""),
            last_name=user_row.get("last_name", ""),
            status=user_row["status"],
        )
