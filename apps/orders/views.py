"""Order and checkout API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from services.order_service import checkout, get_my_orders, transition_order_status
from repositories.order_repository import (
    get_order_with_details, get_order_owner_id,
    get_customer_orders, get_all_orders_admin, get_seller_orders,
)
from permissions.role_permissions import IsCustomerOrAdmin, IsAdmin, IsSellerOrAdmin
from database.query_helpers import serialize_row, fetch_scalar


def _seller_has_product_in_order(seller_id, order_id):
    """Return True if the order contains at least one product owned by this seller."""
    count = fetch_scalar(
        """SELECT COUNT(*) FROM order_items oi
           INNER JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = %s AND p.seller_id = %s""",
        [order_id, seller_id],
    )
    return (count or 0) > 0


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
@permission_classes([IsAuthenticated])
def my_orders(request):
    """GET /api/v1/orders/ — customer: own orders | seller: orders with their products | admin: all."""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    role = request.user.role
    if role == "admin":
        rows, total = get_all_orders_admin(
            status=request.GET.get("status"),
            search=request.GET.get("search"),
            page=page, page_size=page_size,
        )
    elif role == "seller":
        rows, total = get_seller_orders(
            seller_id=request.user.id,
            status=request.GET.get("status"),
            search=request.GET.get("search"),
            page=page, page_size=page_size,
        )
    else:
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

    role     = request.user.role
    user_id  = request.user.id
    owner_id = get_order_owner_id(order_id)

    if role == "admin":
        pass  # admins see all orders
    elif owner_id == user_id:
        pass  # customer who placed the order
    elif role == "seller":
        # Sellers may view orders that contain at least one of their products
        seller_has_item = _seller_has_product_in_order(user_id, order_id)
        if not seller_has_item:
            return error_response(
                "You do not have access to this order",
                "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN,
            )
    else:
        return error_response(
            "You do not have access to this order",
            "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN,
        )

    return success_response(serialize_row(order))


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_status_view(request, order_id):
    """PATCH /api/v1/orders/{id}/status/
    Role-based transition rules enforced server-side:
      admin   — full state machine
      seller  — PAID→PROCESSING, PROCESSING→SHIPPED, only on orders with their products
      customer— no updates allowed
    """
    role     = request.user.role
    user_id  = request.user.id

    # Customers: can only cancel their own orders at PENDING_PAYMENT or PAID
    if role == "customer":
        owner_id = get_order_owner_id(order_id)
        if owner_id != user_id:
            return error_response("You do not own this order",
                                  "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get("status")
        if new_status != "CANCELLED":
            return error_response("Customers may only cancel orders",
                                  "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN)
        from repositories.order_repository import get_order_status as _get_status
        current = _get_status(order_id)
        if current not in ("PENDING_PAYMENT", "PAID"):
            return error_response(
                f"Orders in {current} status cannot be cancelled",
                "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            affected = transition_order_status(order_id, "CANCELLED", user_id)
        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
        return success_response({"updated": affected})

    new_status = request.data.get("status")
    if not new_status:
        return error_response("status is required", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST)

    if role == "seller":
        # Verify this order contains at least one of the seller's products
        if not _seller_has_product_in_order(user_id, order_id):
            return error_response("You do not have access to this order",
                                  "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN)
        # Restrict to seller-allowed transitions only
        SELLER_ALLOWED = {"PAID": {"PROCESSING"}, "PROCESSING": {"SHIPPED"}}
        from repositories.order_repository import get_order_status as _get_status
        current = _get_status(order_id)
        if new_status not in SELLER_ALLOWED.get(current or "", set()):
            return error_response(
                f"Sellers may only transition PAID->PROCESSING or PROCESSING->SHIPPED "
                f"(current: {current})",
                "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN,
            )

    elif role == "admin":
        pass  # admins use the full state machine in transition_order_status

    else:
        return error_response("Not authorized", "PERMISSION_DENIED",
                              status=status.HTTP_403_FORBIDDEN)

    try:
        affected = transition_order_status(order_id, new_status, user_id)
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    return success_response({"updated": affected})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def create_shipment_view(request, order_id):
    """POST /api/v1/orders/{id}/shipments/ — admin creates/updates a shipment record."""
    from database.query_helpers import insert_one, fetch_one as repo_fetch_one
    from repositories.order_repository import get_order_by_id as _get_order

    order = _get_order(order_id)
    if not order:
        return error_response("Order not found", "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
    if order.get("status") not in ("PAID", "PROCESSING", "SHIPPED"):
        return error_response(
            "Shipment can only be created for PAID, PROCESSING or SHIPPED orders.",
            "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST,
        )

    data = request.data
    shipment_id = insert_one(
        """INSERT INTO shipments (order_id, carrier, tracking_number, status)
           VALUES (%s, %s, %s, 'shipped')""",
        [order_id, data.get("carrier", ""), data.get("tracking_number", "")],
    )
    shipment = repo_fetch_one(
        "SELECT id, order_id, carrier, tracking_number, status, created_at FROM shipments WHERE id = %s",
        [shipment_id],
    )
    # Auto-advance order to SHIPPED
    try:
        transition_order_status(order_id, "SHIPPED", request.user.id)
    except ValueError:
        pass  # Already SHIPPED is fine

    return success_response(serialize_row(shipment), status=status.HTTP_201_CREATED)
