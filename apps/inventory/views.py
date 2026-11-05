"""Inventory management API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from repositories.inventory_repository import (
    add_stock, get_variant_stock, get_inventory_movements,
    get_low_stock_products, reconcile_stock,
)
from repositories.product_repository import get_product_owner_id
from database.query_helpers import fetch_one, fetch_all, serialize_row, serialize_rows
from permissions.role_permissions import IsSellerOrAdmin


def _seller_variant_ids(seller_id):
    """Return the set of variant IDs that belong to the given seller."""
    rows = fetch_all(
        """SELECT pv.id FROM product_variants pv
           INNER JOIN products p ON pv.product_id = p.id
           WHERE p.seller_id = %s""",
        [seller_id],
    )
    return {r["id"] for r in rows}


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def add_stock_view(request):
    """POST /api/v1/inventory/add-stock/"""
    data = request.data
    # Validate required fields + types
    try:
        variant_id = int(data["variant_id"])
        quantity   = int(data["quantity"])
    except (KeyError, TypeError, ValueError):
        return error_response("variant_id and quantity must be integers",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    if quantity < 1:
        return error_response("quantity must be at least 1",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    # Sellers may only adjust their own variants
    if request.user.role == "seller":
        owner_id = fetch_one(
            "SELECT p.seller_id FROM product_variants pv "
            "INNER JOIN products p ON pv.product_id = p.id WHERE pv.id = %s",
            [variant_id],
        )
        if not owner_id or owner_id["seller_id"] != request.user.id:
            return error_response("You do not own this variant", "PERMISSION_DENIED",
                                  status=status.HTTP_403_FORBIDDEN)

    new_stock = add_stock(
        variant_id=variant_id,
        quantity=quantity,
        reason=data.get("reason", "restock"),
    )
    return success_response({"variant_id": variant_id, "new_stock": new_stock})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def variant_stock(request, variant_id):
    """GET /api/v1/inventory/variants/{id}/"""
    # Scope check for sellers
    if request.user.role == "seller":
        owner = fetch_one(
            "SELECT p.seller_id FROM product_variants pv "
            "INNER JOIN products p ON pv.product_id = p.id WHERE pv.id = %s",
            [variant_id],
        )
        if not owner or owner["seller_id"] != request.user.id:
            return error_response("You do not own this variant", "PERMISSION_DENIED",
                                  status=status.HTTP_403_FORBIDDEN)
    stock = get_variant_stock(variant_id)
    if not stock:
        return error_response("Variant not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(stock))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def movements(request):
    """GET /api/v1/inventory/movements/
    Sellers see only their own products' movements; admins see all.
    """
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    # Validate & parse optional variant_id
    variant_id_raw = request.GET.get("variant_id")
    variant_id = None
    if variant_id_raw is not None:
        try:
            variant_id = int(variant_id_raw)
        except ValueError:
            return error_response("variant_id must be an integer",
                                  "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    movement_type = request.GET.get("movement_type")

    # For sellers, scope to their variants
    seller_id = request.user.id if request.user.role == "seller" else None

    rows, total = get_inventory_movements(
        variant_id=variant_id,
        movement_type=movement_type,
        seller_id=seller_id,
        page=page, page_size=page_size,
    )
    return paginated_response(rows, total, page, page_size)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def low_stock(request):
    """GET /api/v1/inventory/low-stock/
    Sellers see only their own products; admins see all.
    """
    try:
        threshold = int(request.GET.get("threshold", 10))
    except ValueError:
        threshold = 10

    seller_id = request.user.id if request.user.role == "seller" else None
    products = get_low_stock_products(threshold, seller_id=seller_id)
    return success_response(serialize_rows(products))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def reconcile(request, variant_id):
    """GET /api/v1/inventory/reconcile/{variant_id}/"""
    if request.user.role == "seller":
        owner = fetch_one(
            "SELECT p.seller_id FROM product_variants pv "
            "INNER JOIN products p ON pv.product_id = p.id WHERE pv.id = %s",
            [variant_id],
        )
        if not owner or owner["seller_id"] != request.user.id:
            return error_response("You do not own this variant", "PERMISSION_DENIED",
                                  status=status.HTTP_403_FORBIDDEN)
    result = reconcile_stock(variant_id)
    if not result:
        return error_response("Variant not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(result))
