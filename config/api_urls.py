"""Versioned API URL routing — all endpoints under /api/v1/."""
from django.urls import include, path

urlpatterns = [
    # Authentication
    path("auth/", include("apps.authentication.urls")),
    # Users & Addresses
    path("users/", include("apps.users.urls")),
    # Products & Categories
    path("products/", include("apps.products.urls")),
    # Cart
    path("cart/", include("apps.carts.urls")),
    # Orders
    path("orders/", include("apps.orders.urls")),
    # Payments
    path("payments/", include("apps.payments.urls")),
    # Inventory
    path("inventory/", include("apps.inventory.urls")),
    # Reviews
    path("reviews/", include("apps.reviews.urls")),
    # Analytics & Reports
    path("analytics/", include("apps.analytics.urls")),
    path("reports/", include("apps.analytics.urls")),
]
