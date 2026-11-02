"""
Inventory repository - stock management with atomic operations.

Stock model:
  stock_quantity    - physically on-hand units
  reserved_quantity - units locked for pending orders (not yet shipped)
  available_stock    = stock_quantity - reserved_quantity
"""
import logging
from datetime import datetime
from database.query_helpers import fetch_one, fetch_all, fetch_scalar, insert_one, update_or_delete, fetch_paginated

logger = logging.getLogger("shopflow.repositories.inventory")


def get_variant_stock(variant_id):
    sql = """SELECT id AS variant_id, sku, product_id, price, stock_quantity, reserved_quantity,
             (stock_quantity - reserved_quantity) AS available_stock, status FROM product_variants WHERE id = %s"""
    return fetch_one(sql, [variant_id])


def get_variant_for_update(variant_id):
    sql = """SELECT id, sku, product_id, price, stock_quantity, reserved_quantity,
             (stock_quantity - reserved_quantity) AS available_stock, status
             FROM product_variants WHERE id = %s FOR UPDATE"""
    return fetch_one(sql, [variant_id])


def reserve_stock(variant_id, quantity):
    sql = """UPDATE product_variants SET reserved_quantity = reserved_quantity + %s, updated_at = %s
             WHERE id = %s AND (stock_quantity - reserved_quantity) >= %s"""
    return update_or_delete(sql, [quantity, datetime.utcnow(), variant_id, quantity])


def release_reserved(variant_id, quantity):
    sql = """UPDATE product_variants SET reserved_quantity = GREATEST(0, reserved_quantity - %s), updated_at = %s
             WHERE id = %s"""
    return update_or_delete(sql, [quantity, datetime.utcnow(), variant_id])


def confirm_deduct_stock(variant_id, quantity):
    sql = """UPDATE product_variants SET stock_quantity = stock_quantity - %s,
             reserved_quantity = GREATEST(0, reserved_quantity - %s), updated_at = %s WHERE id = %s"""
    return update_or_delete(sql, [quantity, quantity, datetime.utcnow(), variant_id])


def add_stock(variant_id, quantity, reason="restock"):
    sql = "UPDATE product_variants SET stock_quantity = stock_quantity + %s, updated_at = %s WHERE id = %s"
    affected = update_or_delete(sql, [quantity, datetime.utcnow(), variant_id])
    if affected > 0:
        record_movement(variant_id, "stock_in", quantity, reason)
    variant = get_variant_stock(variant_id)
    return variant["stock_quantity"] if variant else 0


def record_movement(variant_id, movement_type, quantity, reason="", order_id=None, reference_type=None, reference_id=None):
    sql = """INSERT INTO inventory_movements (variant_id, movement_type, quantity, reason, order_id, reference_type, reference_id)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    return insert_one(sql, [variant_id, movement_type, quantity, reason, order_id, reference_type, reference_id])


def get_inventory_movements(variant_id=None, movement_type=None, page=1, page_size=20):
    conditions, params = [], []
    if variant_id is not None: conditions.append("im.variant_id = %s"); params.append(variant_id)
    if movement_type is not None: conditions.append("im.movement_type = %s"); params.append(movement_type)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""SELECT im.id, im.variant_id, pv.sku, p.name AS product_name, im.movement_type, im.quantity,
             im.reason, im.order_id, im.reference_type, im.reference_id, im.created_at
             FROM inventory_movements im INNER JOIN product_variants pv ON im.variant_id = pv.id
             INNER JOIN products p ON pv.product_id = p.id {where_clause} ORDER BY im.created_at DESC"""
    return fetch_paginated(sql, params, page, page_size)


def get_low_stock_products(threshold=10):
    sql = """SELECT pv.id AS variant_id, pv.sku, pv.variant_name, pv.stock_quantity, pv.reserved_quantity,
             (pv.stock_quantity - pv.reserved_quantity) AS available_stock,
             p.id AS product_id, p.name AS product_name,
             u.first_name AS seller_first_name, u.last_name AS seller_last_name, u.email AS seller_email
             FROM product_variants pv INNER JOIN products p ON pv.product_id = p.id
             INNER JOIN users u ON p.seller_id = u.id
             WHERE pv.status = 'active' AND (pv.stock_quantity - pv.reserved_quantity) < %s
             ORDER BY available_stock ASC"""
    return fetch_all(sql, [threshold])


def reconcile_stock(variant_id):
    sql = """SELECT pv.stock_quantity AS recorded_stock, pv.reserved_quantity AS recorded_reserved,
             COALESCE(SUM(CASE WHEN im.movement_type = 'stock_in' THEN im.quantity ELSE 0 END), 0) AS total_stock_in,
             COALESCE(SUM(CASE WHEN im.movement_type = 'sale' THEN im.quantity ELSE 0 END), 0) AS total_sold,
             COALESCE(SUM(CASE WHEN im.movement_type = 'adjustment' THEN im.quantity ELSE 0 END), 0) AS total_adjustment,
             COALESCE(SUM(CASE WHEN im.movement_type = 'stock_in' THEN im.quantity ELSE 0 END), 0)
             - COALESCE(SUM(CASE WHEN im.movement_type = 'sale' THEN im.quantity ELSE 0 END), 0)
             + COALESCE(SUM(CASE WHEN im.movement_type = 'adjustment' THEN im.quantity ELSE 0 END), 0) AS calculated_stock
             FROM product_variants pv LEFT JOIN inventory_movements im ON im.variant_id = pv.id
             WHERE pv.id = %s GROUP BY pv.id, pv.stock_quantity, pv.reserved_quantity"""
    result = fetch_one(sql, [variant_id])
    if result: result["is_balanced"] = (result["recorded_stock"] == result["calculated_stock"])
    return result or {}
