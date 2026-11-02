"""Order and checkout API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from services.order_service import checkout, get_my_orders, transition_order_status
from repositories.order_repository import get_order_with_details, get_order_owner_id
from permissions.role_permissions import IsCustomerOrAdmin
from database.query_helpers import serialize_row


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def checkout_view(request):
    """POST /api/v1/orders/checkout/"""
    data = request.data
    if not data.get("shipping_address_id"):
        return error_response("shipping_address_id is required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    try:
        order = checkout(
            user_id=request.user.id,
            shipping_address_id=data["shipping_address_id"],
            coupon_code=data.get("coupon_code"),
            idempotency_key=data.get("idempotency_key"),
        )
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    return success_response(order, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def my_orders(request):
    """GET /api/v1/orders/"""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    rows, total = get_my_orders(
        request.user.id,
        status=request.GET.get("status"),
        page=page, page_size=page_size,
    )
    return paginated_response(rows, total, page, page_size)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """GET /api/v1/orders/{id}/"""
    order = get_order_with_details(order_id)
    if not order:
        return error_response("Order not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)

    # Ownership check
    owner_id = get_order_owner_id(order_id)
    if owner_id != request.user.id and request.user.role != "admin":
        return error_response("You do not have access to this order",
                              "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN)

    return success_response(serialize_row(order))


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_status_view(request, order_id):
    """PATCH /api/v1/orders/{id}/status/"""
    # Ownership/admin check
    owner_id = get_order_owner_id(order_id)
    if owner_id != request.user.id and request.user.role not in ("admin", "seller"):
        return error_response("Not authorized to update this order",
                              "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get("status")
    if not new_status:
        return error_response("status is required", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST)

    try:
        affected = transition_order_status(order_id, new_status, request.user.id)
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    return success_response({"updated": affected})
