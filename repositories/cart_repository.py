"""Cart repository - shopping cart SQL operations."""
import logging
from database.query_helpers import fetch_one, fetch_all, fetch_scalar, insert_one, update_or_delete

logger = logging.getLogger("shopflow.repositories.cart")


def get_or_create_cart(user_id):
    cart = fetch_one("SELECT id FROM carts WHERE user_id = %s", [user_id])
    if cart: return cart["id"]
    return insert_one("INSERT INTO carts (user_id) VALUES (%s)", [user_id])


def get_cart_items(cart_id):
    sql = """SELECT ci.id AS cart_item_id, ci.cart_id, ci.variant_id, ci.quantity, ci.added_at,
             pv.sku, pv.variant_name, pv.price AS unit_price, pv.stock_quantity, pv.reserved_quantity,
             (pv.stock_quantity - pv.reserved_quantity) AS available_stock,
             p.id AS product_id, p.name AS product_name, p.status AS product_status, p.slug AS product_slug,
             (SELECT image_url FROM product_images pi WHERE pi.product_id = p.id ORDER BY display_order ASC LIMIT 1) AS image_url
             FROM cart_items ci INNER JOIN product_variants pv ON ci.variant_id = pv.id
             INNER JOIN products p ON pv.product_id = p.id WHERE ci.cart_id = %s ORDER BY ci.added_at ASC"""
    return fetch_all(sql, [cart_id])


def add_cart_item(cart_id, variant_id, quantity):
    sql = """INSERT INTO cart_items (cart_id, variant_id, quantity) VALUES (%s, %s, %s)
             ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)"""
    insert_one(sql, [cart_id, variant_id, quantity])
    item = fetch_one("SELECT id FROM cart_items WHERE cart_id = %s AND variant_id = %s", [cart_id, variant_id])
    return item["id"] if item else 0


def update_cart_item_quantity(cart_id, variant_id, quantity):
    return update_or_delete("UPDATE cart_items SET quantity = %s WHERE cart_id = %s AND variant_id = %s",
                            [quantity, cart_id, variant_id])


def remove_cart_item(cart_id, variant_id):
    return update_or_delete("DELETE FROM cart_items WHERE cart_id = %s AND variant_id = %s", [cart_id, variant_id])


def clear_cart(cart_id):
    return update_or_delete("DELETE FROM cart_items WHERE cart_id = %s", [cart_id])


def get_cart_item_count(cart_id):
    return fetch_scalar("SELECT COUNT(*) FROM cart_items WHERE cart_id = %s", [cart_id]) or 0


def get_cart_subtotal(cart_id):
    result = fetch_one("""SELECT COALESCE(SUM(ci.quantity * pv.price), 0) AS subtotal
                          FROM cart_items ci INNER JOIN product_variants pv ON ci.variant_id = pv.id
                          WHERE ci.cart_id = %s""", [cart_id])
    return float(result["subtotal"]) if result else 0.0
