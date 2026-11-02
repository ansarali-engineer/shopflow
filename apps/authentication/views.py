"""Authentication API views."""
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response
from utils.validators import validate_email, validate_password
from services.auth_service import (
    register_user, login_user, refresh_access_token, change_password,
)
from repositories.user_repository import (
    get_user_profile, update_user_profile,
)
from database.query_helpers import serialize_row
from apps.authentication.serializers import (
    RegisterSerializer, LoginSerializer, RefreshTokenSerializer,
    ChangePasswordSerializer, UpdateProfileSerializer,
)
from .throttles import LoginRateThrottle

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """POST /api/v1/auth/register/"""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response("Validation error", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST,
                              details=serializer.errors)

    data = serializer.validated_data
    try:
        user, tokens = register_user(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=data["role"],
            phone=data.get("phone"),
        )
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR",
                               status=status.HTTP_409_CONFLICT)

    return success_response(
        {"user": serialize_row(user), **tokens},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login(request):
    """POST /api/v1/auth/login/"""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response("Validation error", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST,
                              details=serializer.errors)

    data = serializer.validated_data
    user, tokens = login_user(data["email"], data["password"])

    if user is None:
        return error_response("Invalid email or password", "AUTHENTICATION_FAILED",
                              status=status.HTTP_401_UNAUTHORIZED)

    user.pop("password_hash", None)
    return success_response({"user": serialize_row(user), **tokens})


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    """POST /api/v1/auth/refresh/"""
    serializer = RefreshTokenSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response("Validation error", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST,
                              details=serializer.errors)

    try:
        access = refresh_access_token(serializer.validated_data["refresh_token"])
    except Exception:
        return error_response("Invalid or expired refresh token", "AUTHENTICATION_FAILED",
                              status=status.HTTP_401_UNAUTHORIZED)

    return success_response({"access_token": access})


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET/PUT /api/v1/auth/me/"""
    user_id = request.user.id

    if request.method == "GET":
        profile = get_user_profile(user_id)
        if not profile:
            return error_response("User not found", "NOT_FOUND",
                                   status=status.HTTP_404_NOT_FOUND)
        return success_response(serialize_row(profile))

    elif request.method == "PUT":
        serializer = UpdateProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", "VALIDATION_ERROR",
                                  status=status.HTTP_400_BAD_REQUEST,
                                  details=serializer.errors)

        data = serializer.validated_data
        update_user_profile(
            user_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
        )
        profile = get_user_profile(user_id)
        return success_response(serialize_row(profile))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """POST /api/v1/auth/change-password/"""
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response("Validation error", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST,
                              details=serializer.errors)

    data = serializer.validated_data
    try:
        change_password(request.user.id, data["old_password"], data["new_password"])
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR",
                               status=status.HTTP_400_BAD_REQUEST)

    return success_response({"message": "Password updated successfully"})
