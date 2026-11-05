"""
Order repository - order creation, retrieval, and status management SQL.
"""
import logging
from datetime import datetime
from database.query_helpers import fetch_one, fetch_all, fetch_scalar, insert_one, update_or_delete, insert_many, fetch_paginated

logger = logging.getLogger("shopflow.repositories.order")

VALID_TRANSITIONS = {
    "PENDING_PAYMENT": {"PAID", "CANCELLED"},
    "PAID": {"PROCESSING", "CANCELLED", "REFUNDED"},
    "PROCESSING": {"SHIPPED", "REFUNDED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": {"RETURNED"},
}


def create_order(customer_id, order_number, subtotal, discount_amount, shipping_cost, tax_amount,
                  total_amount, shipping_address_id, coupon_id=None, status="PENDING_PAYMENT"):
    sql = """INSERT INTO orders (customer_id, order_number, status, subtotal, discount_amount, shipping_cost,
             tax_amount, total_amount, shipping_address_id, coupon_id)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    return insert_one(sql, [customer_id, order_number, status, subtotal, discount_amount, shipping_cost,
                           tax_amount, total_amount, shipping_address_id, coupon_id])


def bulk_insert_order_items(items):
    sql = "INSERT INTO order_items (order_id, product_id, variant_id, quantity, unit_price, line_total) VALUES (%s, %s, %s, %s, %s, %s)"
    return insert_many(sql, items)


def get_order_by_id(order_id):
    sql = """SELECT o.id, o.order_number, o.customer_id, o.status, o.subtotal, o.discount_amount,
             o.shipping_cost, o.tax_amount, o.total_amount, o.shipping_address_id, o.coupon_id,
             o.created_at, o.updated_at, c.email AS customer_email,
             c.first_name AS customer_first_name, c.last_name AS customer_last_name
             FROM orders o INNER JOIN users c ON o.customer_id = c.id WHERE o.id = %s"""
    return fetch_one(sql, [order_id])


def get_order_with_details(order_id):
    order = get_order_by_id(order_id)
    if not order: return None
    sql_items = """SELECT oi.id, oi.order_id, oi.product_id, oi.variant_id, oi.quantity, oi.unit_price, oi.line_total,
             p.name AS product_name, p.slug AS product_slug, pv.sku AS variant_sku, pv.variant_name,
             (SELECT pi.image_url FROM product_images pi
              WHERE pi.product_id = p.id
              ORDER BY pi.display_order ASC, pi.id ASC LIMIT 1) AS image_url
             FROM order_items oi INNER JOIN products p ON oi.product_id = p.id
             INNER JOIN product_variants pv ON oi.variant_id = pv.id WHERE oi.order_id = %s ORDER BY oi.id ASC"""
    order["items"] = fetch_all(sql_items, [order_id])
    sql_payments = """SELECT id, order_id, payment_method, amount, status, transaction_ref, idempotency_key, created_at, updated_at
             FROM payments WHERE order_id = %s ORDER BY created_at ASC"""
    order["payments"] = fetch_all(sql_payments, [order_id])
    sql_shipments = """SELECT id, order_id, carrier, tracking_number, shipped_at, delivered_at, status, created_at
             FROM shipments WHERE order_id = %s ORDER BY created_at DESC"""
    order["shipments"] = fetch_all(sql_shipments, [order_id])
    return order


def get_customer_orders(customer_id, status=None, page=1, page_size=20):
    conditions = ["o.customer_id = %s"]
    params = [customer_id]
    if status: conditions.append("o.status = %s"); params.append(status)
    where_clause = " AND ".join(conditions)
    sql = f"""SELECT o.id, o.order_number, o.status, o.total_amount, o.created_at,
             (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS item_count,
             (SELECT GROUP_CONCAT(p.name SEPARATOR ', ') FROM order_items oi
              INNER JOIN products p ON oi.product_id = p.id WHERE oi.order_id = o.id) AS product_names,
             CASE WHEN o.status IN ('DELIVERED') THEN 'completed'
                  WHEN o.status IN ('CANCELLED','REFUNDED') THEN 'cancelled'
                  WHEN o.status IN ('SHIPPED') THEN 'shipped'
                  ELSE 'processing' END AS order_stage
             FROM orders o WHERE {where_clause} ORDER BY o.created_at DESC"""
    return fetch_paginated(sql, params, page, page_size)


def get_order_owner_id(order_id):
    return fetch_scalar("SELECT customer_id FROM orders WHERE id = %s", [order_id])


def get_seller_orders(seller_id, status=None, search=None, page=1, page_size=20):
    """Orders that contain at least one product owned by the given seller."""
    conditions = ["p.seller_id = %s"]
    params = [seller_id]
    if status:
        conditions.append("o.status = %s"); params.append(status)
    if search:
        conditions.append(
            "(o.order_number LIKE %s OR u.email LIKE %s)"
        )
        like = f"%{search}%"; params.extend([like, like])
    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT DISTINCT
               o.id, o.order_number, o.status, o.total_amount, o.created_at,
               o.customer_id,
               u.email      AS customer_email,
               u.first_name AS customer_first_name,
               u.last_name  AS customer_last_name,
               (SELECT COUNT(*) FROM order_items oi2 WHERE oi2.order_id = o.id) AS item_count,
               (SELECT GROUP_CONCAT(DISTINCT p2.name SEPARATOR ', ')
                FROM order_items oi2
                INNER JOIN products p2 ON oi2.product_id = p2.id
                WHERE oi2.order_id = o.id AND p2.seller_id = %s) AS seller_product_names
        FROM orders o
        INNER JOIN users      u  ON o.customer_id = u.id
        INNER JOIN order_items oi ON oi.order_id   = o.id
        INNER JOIN products   p  ON oi.product_id  = p.id
        {where}
        ORDER BY o.created_at DESC
    """
    # seller_id appears twice in the query (GROUP_CONCAT subquery + WHERE)
    return fetch_paginated(sql, params + [seller_id], page, page_size)


def get_all_orders_admin(status=None, search=None, page=1, page_size=20):
    """Admin-scope: all orders with customer info and item summary."""
    conditions, params = [], []
    if status:
        conditions.append("o.status = %s"); params.append(status)
    if search:
        conditions.append(
            "(o.order_number LIKE %s OR u.email LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s)"
        )
        like = f"%{search}%"
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT o.id, o.order_number, o.status, o.total_amount, o.created_at,
               o.customer_id,
               u.email      AS customer_email,
               u.first_name AS customer_first_name,
               u.last_name  AS customer_last_name,
               (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS item_count,
               (SELECT GROUP_CONCAT(p.name SEPARATOR ', ')
                FROM order_items oi INNER JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = o.id) AS product_names
        FROM orders o
        INNER JOIN users u ON o.customer_id = u.id
        {where}
        ORDER BY o.created_at DESC
    """
    return fetch_paginated(sql, params, page, page_size)


def update_order_status(order_id, new_status):
    return update_or_delete("UPDATE orders SET status = %s, updated_at = %s WHERE id = %s",
                           [new_status, datetime.utcnow(), order_id])


def get_order_status(order_id):
    return fetch_scalar("SELECT status FROM orders WHERE id = %s", [order_id])


def generate_order_number():
    prefix = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-"
    count = fetch_scalar("SELECT COUNT(*) FROM orders WHERE order_number LIKE %s", [f"{prefix}%"]) or 0
    return f"{prefix}{count + 1:05d}"


def get_order_status_summary():
    sql = """SELECT status, COUNT(*) AS order_count, COALESCE(SUM(total_amount), 0) AS total_value
             FROM orders GROUP BY status ORDER BY total_value DESC"""
    return fetch_all(sql)
