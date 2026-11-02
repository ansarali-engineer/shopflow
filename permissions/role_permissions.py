"""
Custom DRF permission classes for role-based access control.

Roles:
    customer — Can browse, buy, review, manage own cart/orders
    seller   — Can manage own products, inventory, view own orders
    admin    — Full access to all resources and reports

Object-level permissions enforce ownership:
    - Sellers can only see/modify their own products
    - Customers can only see/modify their own cart/orders/addresses
"""
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated as DRFIsAuthenticated,
)


class IsAuthenticated(DRFIsAuthenticated):
    """Must be authenticated via JWT."""
    pass


class IsCustomer(BasePermission):
    """Only customers can access this endpoint."""
    def has_permission(self, request, view):
        return (
            bool(request.user)
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "customer"
        )


class IsSeller(BasePermission):
    """Only sellers can access this endpoint."""
    def has_permission(self, request, view):
        return (
            bool(request.user)
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "seller"
        )


class IsAdmin(BasePermission):
    """Only admins can access this endpoint."""
    def has_permission(self, request, view):
        return (
            bool(request.user)
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "admin"
        )


class IsCustomerOrAdmin(BasePermission):
    """Customers and admins can access; sellers cannot."""
    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = getattr(request.user, "role", None)
        return role in ("customer", "admin")


class IsSellerOrAdmin(BasePermission):
    """Sellers and admins can access."""
    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        role = getattr(request.user, "role", None)
        return role in ("seller", "admin")


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: user must own the resource or be admin.

    The view must set request.resource_owner_id or implement
    check_object_permission().
    """
    def has_object_permission(self, request, view, obj):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if getattr(request.user, "role", None) == "admin":
            return True
        owner_id = getattr(obj, "user_id", None) or getattr(obj, "customer_id", None)
        return owner_id == getattr(request.user, "id", None)


class IsSellerOwnerOrAdmin(BasePermission):
    """
    Object-level: seller must own the product, or be admin.
    """
    def has_object_permission(self, request, view, obj):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if getattr(request.user, "role", None) == "admin":
            return True
        seller_id = getattr(obj, "seller_id", None)
        return seller_id == getattr(request.user, "id", None)
