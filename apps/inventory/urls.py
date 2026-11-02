"""Inventory URL routes."""
from django.urls import path
from apps.inventory.views import add_stock_view, variant_stock, movements, low_stock, reconcile

urlpatterns = [
    path("add-stock/", add_stock_view),
    path("variants/<int:variant_id>/", variant_stock),
    path("movements/", movements),
    path("low-stock/", low_stock),
    path("reconcile/<int:variant_id>/", reconcile),
]
