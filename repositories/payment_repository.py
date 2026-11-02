"""
Payment repository - payment record SQL operations with idempotency.
"""
import logging
from datetime import datetime
from database.query_helpers import fetch_one, fetch_all, insert_one, update_or_delete

logger = logging.getLogger("shopflow.repositories.payment")


def create_payment(order_id, payment_method, amount, idempotency_key=None):
    sql = "INSERT INTO payments (order_id, payment_method, amount, status, idempotency_key) VALUES (%s, %s, %s, 'pending', %s)"
    return insert_one(sql, [order_id, payment_method, amount, idempotency_key])


def get_payment_by_id(payment_id):
    sql = """SELECT id, order_id, payment_method, amount, status, transaction_ref, idempotency_key, failure_reason, created_at, updated_at
             FROM payments WHERE id = %s"""
    return fetch_one(sql, [payment_id])


def get_payment_by_idempotency_key(key):
    sql = "SELECT id, order_id, amount, status, transaction_ref FROM payments WHERE idempotency_key = %s"
    return fetch_one(sql, [key])


def get_payments_by_order(order_id):
    sql = """SELECT id, order_id, payment_method, amount, status, transaction_ref, idempotency_key, failure_reason, created_at, updated_at
             FROM payments WHERE order_id = %s ORDER BY created_at ASC"""
    return fetch_all(sql, [order_id])


def update_payment_status(payment_id, status, transaction_ref=None, failure_reason=None):
    sql = """UPDATE payments SET status = %s, transaction_ref = COALESCE(%s, transaction_ref),
             failure_reason = COALESCE(%s, failure_reason), updated_at = %s WHERE id = %s"""
    return update_or_delete(sql, [status, transaction_ref, failure_reason, datetime.utcnow(), payment_id])


def check_duplicate_callback(transaction_ref):
    sql = "SELECT id, order_id, status, amount FROM payments WHERE transaction_ref = %s"
    return fetch_one(sql, [transaction_ref])
