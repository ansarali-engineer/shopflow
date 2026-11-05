"""Order URL routes."""
from django.urls import path
from apps.orders.views import (
    checkout_view, my_orders, order_detail,
    update_order_status_view, create_shipment_view,
)

urlpatterns = [
    path("checkout/", checkout_view),
    path("", my_orders),
    path("<int:order_id>/", order_detail),
    path("<int:order_id>/status/", update_order_status_view),
    path("<int:order_id>/shipments/", create_shipment_view),
]
