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
from permissions.role_permissions import IsSellerOrAdmin
from database.query_helpers import serialize_row, serialize_rows


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def add_stock_view(request):
    """POST /api/v1/inventory/add-stock/"""
    data = request.data
    if not data.get("variant_id") or not data.get("quantity"):
        return error_response("variant_id and quantity are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    new_stock = add_stock(
        variant_id=data["variant_id"],
        quantity=data["quantity"],
        reason=data.get("reason", "restock"),
    )
    return success_response({"variant_id": data["variant_id"], "new_stock": new_stock})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def variant_stock(request, variant_id):
    """GET /api/v1/inventory/variants/{id}/"""
    stock = get_variant_stock(variant_id)
    if not stock:
        return error_response("Variant not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(stock))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def movements(request):
    """GET /api/v1/inventory/movements/"""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    rows, total = get_inventory_movements(
        variant_id=request.GET.get("variant_id"),
        movement_type=request.GET.get("movement_type"),
        page=page, page_size=page_size,
    )
    return paginated_response(rows, total, page, page_size)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def low_stock(request):
    """GET /api/v1/inventory/low-stock/"""
    threshold = int(request.GET.get("threshold", 10))
    products = get_low_stock_products(threshold)
    return success_response(serialize_rows(products))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def reconcile(request, variant_id):
    """GET /api/v1/inventory/reconcile/{variant_id}/"""
    result = reconcile_stock(variant_id)
    if not result:
        return error_response("Variant not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(result))
