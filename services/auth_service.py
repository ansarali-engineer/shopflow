"""
Authentication service - registration, login, token generation.

Business rules:
  - Email must be unique (enforced by DB constraint)
  - Password hashed with Django's make_password (Argon2)
  - JWT tokens generated with Simple JWT
  - Cart auto-created on registration for customers
"""
import logging
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken

from repositories.user_repository import (
    create_user, authenticate_user, get_user_by_id,
    update_user_profile, update_user_status, update_password,
)
from repositories.cart_repository import get_or_create_cart
from database.connection import DuplicateRecordError

logger = logging.getLogger("shopflow.services.auth")


def register_user(email, password, first_name, last_name, role="customer", phone=None):
    """
    Register a new user. Returns (user_dict, tokens).

    Raises ValueError for invalid input.
    Raises DuplicateRecordError if email exists.
    """
    from utils.validators import validate_email, validate_password

    email = validate_email(email)
    validate_password(password)

    if role not in ("customer", "seller", "admin"):
        raise ValueError("Invalid role")

    try:
        user = create_user(email, password, first_name, last_name, role, phone)
    except DuplicateRecordError:
        raise ValueError("An account with this email already exists")

    # Auto-create cart for customers
    if role == "customer":
        get_or_create_cart(user["id"])

    # Generate JWT tokens
    tokens = _generate_tokens(user["id"], user["role"])

    logger.info("User registered: id=%s, role=%s", user["id"], role)
    return user, tokens


def login_user(email, password):
    """
    Authenticate and return (user_dict, tokens).

    Returns None if credentials are invalid.
    """
    user = authenticate_user(email, password)
    if user is None:
        logger.warning("Failed login attempt for email=%s", email)
        return None, None

    tokens = _generate_tokens(user["id"], user["role"])
    logger.info("User logged in: id=%s", user["id"])
    return user, tokens


def _generate_tokens(user_id: int, role: str) -> dict:
    """Generate JWT access and refresh tokens."""
    refresh = RefreshToken()
    refresh["user_id"] = user_id
    refresh["role"] = role

    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }


def refresh_access_token(refresh_token_str: str) -> str:
    """Generate a new access token from a refresh token."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken(refresh_token_str)
    return str(refresh.access_token)


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change password after verifying old password."""
    from utils.validators import validate_password

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")

    from repositories.user_repository import verify_password
    if not verify_password(user, old_password):
        raise ValueError("Current password is incorrect")

    validate_password(new_password)
    update_password(user_id, new_password)
    logger.info("Password changed for user_id=%s", user_id)
    return True
