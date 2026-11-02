"""Cart URL routes."""
from django.urls import path
from apps.carts.views import view_cart, add_to_cart, update_cart_item, remove_from_cart, clear_cart_view

urlpatterns = [
    path("", view_cart),
    path("items/", add_to_cart),
    path("items/update/", update_cart_item),
    path("items/<int:variant_id>/", remove_from_cart),
    path("clear/", clear_cart_view),
]
