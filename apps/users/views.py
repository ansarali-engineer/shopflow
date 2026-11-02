"""User profile and address API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from database.connection import DuplicateRecordError
from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from database.query_helpers import serialize_row, serialize_rows
from repositories.user_repository import (
    get_user_profile, update_user_profile,
    create_address, get_addresses_by_user, get_address_by_id,
    update_address, delete_address, list_admin_users, update_admin_user,
    update_user_status,
)
from permissions.role_permissions import IsAdmin
from apps.users.serializers import AdminUserUpdateSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_user_list(request):
    """GET /api/v1/users/ — paginated user directory for administrators."""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    role = request.GET.get("role")
    user_status = request.GET.get("status")
    search = request.GET.get("search", "").strip()

    if role and role not in ("customer", "seller", "admin"):
        return error_response(
            "role must be customer, seller, or admin",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
        )
    if user_status and user_status not in ("active", "suspended", "deleted"):
        return error_response(
            "status must be active, suspended, or deleted",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(search) > 100:
        return error_response(
            "search must be 100 characters or fewer",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
        )

    users, total = list_admin_users(
        page=page,
        page_size=page_size,
        role=role,
        status=user_status,
        search=search,
    )
    return paginated_response(serialize_rows(users), total, page, page_size)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_user_detail(request, user_id):
    """Retrieve, update, or deactivate a user account as an administrator."""
    profile = get_user_profile(user_id)
    if not profile:
        return error_response(
            "User not found", "NOT_FOUND", status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return success_response(serialize_row(profile))

    if request.method == "DELETE":
        if user_id == request.user.id:
            return error_response(
                "You cannot deactivate your own account",
                "VALIDATION_ERROR",
                status=status.HTTP_400_BAD_REQUEST,
            )
        update_user_status(user_id, "deleted")
        return success_response({"id": user_id, "status": "deleted"})

    serializer = AdminUserUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return error_response(
            "Validation error",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
            details=serializer.errors,
        )

    updates = serializer.validated_data
    if not updates:
        return error_response(
            "At least one user field must be provided",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
        )
    if user_id == request.user.id and (
        updates.get("role", request.user.role) != "admin"
        or updates.get("status", request.user.status) != "active"
    ):
        return error_response(
            "You cannot remove your own admin access or deactivate your account",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        update_admin_user(user_id, updates)
    except DuplicateRecordError:
        return error_response(
            "A user with this email already exists",
            "DUPLICATE_EMAIL",
            status=status.HTTP_409_CONFLICT,
        )

    updated_profile = get_user_profile(user_id)
    return success_response(serialize_row(updated_profile))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_profile(request):
    """GET /api/v1/users/me/"""
    profile = get_user_profile(request.user.id)
    if not profile:
        return error_response("User not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(profile))


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_my_profile(request):
    """PUT /api/v1/users/me/"""
    update_user_profile(
        request.user.id,
        first_name=request.data.get("first_name"),
        last_name=request.data.get("last_name"),
        phone=request.data.get("phone"),
    )
    profile = get_user_profile(request.user.id)
    return success_response(serialize_row(profile))


# ── Addresses ──────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def addresses(request):
    if request.method == "GET":
        addrs = get_addresses_by_user(request.user.id)
        return success_response(serialize_rows(addrs))

    data = request.data
    if not data.get("label") or not data.get("street_line1") or not data.get("city"):
        return error_response("label, street_line1, and city are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    addr_id = create_address(
        user_id=request.user.id,
        label=data["label"],
        street_line1=data["street_line1"],
        street_line2=data.get("street_line2"),
        city=data["city"],
        state=data.get("state", ""),
        postal_code=data.get("postal_code", ""),
        country=data.get("country", "US"),
        is_default=data.get("is_default", False),
    )
    return success_response({"address_id": addr_id}, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def address_detail(request, address_id):
    addr = get_address_by_id(address_id, request.user.id)
    if not addr:
        return error_response("Address not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)

    if request.method == "PUT":
        update_address(address_id, request.user.id, **request.data)
        addr = get_address_by_id(address_id, request.user.id)
        return success_response(serialize_row(addr))

    elif request.method == "DELETE":
        delete_address(address_id, request.user.id)
        return success_response({"message": "Address deleted"})
