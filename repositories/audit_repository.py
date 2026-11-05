"""Audit log repository - records of important administrative actions."""
import json
import logging
from database.query_helpers import fetch_one, fetch_all, insert_one, fetch_paginated

logger = logging.getLogger("shopflow.repositories.audit")


def _to_json(value):
    """
    Safely convert any value to a JSON string suitable for a MySQL JSON column.
    - None     → None  (stored as SQL NULL, not the string "null")
    - str      → JSON-encoded string  e.g. '"hello"'
    - dict/list→ JSON-encoded object/array
    - other    → JSON-encoded via str() fallback
    """
    if value is None:
        return None
    if isinstance(value, str):
        # Wrap plain strings as a JSON string value so MySQL accepts them.
        return json.dumps(value)
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return json.dumps(str(value))


def log_action(user_id, action, entity_type, entity_id=None,
               old_values=None, new_values=None, ip_address=None):
    sql = """INSERT INTO audit_logs
             (user_id, action, entity_type, entity_id, old_values, new_values, ip_address)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    try:
        return insert_one(sql, [
            user_id,
            action,
            entity_type,
            entity_id,
            _to_json(old_values),
            _to_json(new_values),
            ip_address,
        ])
    except Exception as exc:
        # Audit failures must never crash the main transaction.
        logger.error("audit log_action failed: %s", exc, exc_info=True)
        return None


def get_audit_logs(user_id=None, action=None, entity_type=None, page=1, page_size=50):
    conditions, params = [], []
    if user_id is not None:
        conditions.append("al.user_id = %s"); params.append(user_id)
    if action:
        conditions.append("al.action = %s"); params.append(action)
    if entity_type:
        conditions.append("al.entity_type = %s"); params.append(entity_type)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""SELECT al.id, al.user_id, u.email AS user_email, al.action, al.entity_type,
             al.entity_id, al.old_values, al.new_values, al.ip_address, al.created_at
             FROM audit_logs al
             LEFT JOIN users u ON al.user_id = u.id
             {where_clause}
             ORDER BY al.created_at DESC"""
    return fetch_paginated(sql, params, page, page_size)
