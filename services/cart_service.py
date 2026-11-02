"""Cart service - shopping cart business logic."""
import logging
from database.query_helpers import serialize_row, serialize_rows
from repositories.cart_repository import (
    get_or_create_cart, get_cart_items, add_cart_item,
    update_cart_item_quantity, remove_cart_item, clear_cart,
    get_cart_item_count, get_cart_subtotal,
)

logger = logging.getLogger("shopflow.services.cart")


def get_user_cart(user_id):
    cart_id = get_or_create_cart(user_id)
    items = get_cart_items(cart_id)
    subtotal = get_cart_subtotal(cart_id)
    count = get_cart_item_count(cart_id)
    return {
        "cart_id": cart_id,
        "items": serialize_rows(items),
        "item_count": count,
        "subtotal": str(subtotal),
    }


def add_item(user_id, variant_id, quantity):
    from utils.validators import validate_quantity
    validate_quantity(quantity)

    cart_id = get_or_create_cart(user_id)
    item_id = add_cart_item(cart_id, variant_id, quantity)
    logger.info("Item added to cart: user=%s, variant=%s, qty=%s", user_id, variant_id, quantity)
    return item_id


def update_item(user_id, variant_id, quantity):
    from utils.validators import validate_quantity
    validate_quantity(quantity)

    cart_id = get_or_create_cart(user_id)
    affected = update_cart_item_quantity(cart_id, variant_id, quantity)
    if affected == 0:
        raise ValueError("Item not found in cart")
    return affected


def remove_item(user_id, variant_id):
    cart_id = get_or_create_cart(user_id)
    affected = remove_cart_item(cart_id, variant_id)
    if affected == 0:
        raise ValueError("Item not found in cart")
    return affected


def clear(user_id):
    cart_id = get_or_create_cart(user_id)
    return clear_cart(cart_id)
