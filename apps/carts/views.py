"""Cart API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response
from services.cart_service import get_user_cart, add_item, update_item, remove_item, clear
from permissions.role_permissions import IsCustomerOrAdmin


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def view_cart(request):
    """GET /api/v1/cart/"""
    cart = get_user_cart(request.user.id)
    return success_response(cart)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def add_to_cart(request):
    """POST /api/v1/cart/items/"""
    data = request.data
    if not data.get("variant_id") or not data.get("quantity"):
        return error_response("variant_id and quantity are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    try:
        item_id = add_item(request.user.id, data["variant_id"], data["quantity"])
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    return success_response({"cart_item_id": item_id}, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def update_cart_item(request):
    """PUT /api/v1/cart/items/"""
    data = request.data
    if not data.get("variant_id") or not data.get("quantity"):
        return error_response("variant_id and quantity are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    try:
        update_item(request.user.id, data["variant_id"], data["quantity"])
    except ValueError as e:
        return error_response(str(e), "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
    return success_response({"message": "Cart item updated"})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def remove_from_cart(request, variant_id):
    """DELETE /api/v1/cart/items/{variant_id}/"""
    try:
        remove_item(request.user.id, variant_id)
    except ValueError as e:
        return error_response(str(e), "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
    return success_response({"message": "Item removed"})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def clear_cart_view(request):
    """DELETE /api/v1/cart/"""
    clear(request.user.id)
    return success_response({"message": "Cart cleared"})
