"""Audit log repository - records of important administrative actions."""
import logging
from database.query_helpers import fetch_one, fetch_all, insert_one, fetch_paginated

logger = logging.getLogger("shopflow.repositories.audit")


def log_action(user_id, action, entity_type, entity_id=None, old_values=None, new_values=None, ip_address=None):
    sql = """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_values, new_values, ip_address)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    return insert_one(sql, [user_id, action, entity_type, entity_id, old_values, new_values, ip_address])


def get_audit_logs(user_id=None, action=None, entity_type=None, page=1, page_size=50):
    conditions, params = [], []
    if user_id is not None: conditions.append("al.user_id = %s"); params.append(user_id)
    if action: conditions.append("al.action = %s"); params.append(action)
    if entity_type: conditions.append("al.entity_type = %s"); params.append(entity_type)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""SELECT al.id, al.user_id, u.email AS user_email, al.action, al.entity_type, al.entity_id,
             al.old_values, al.new_values, al.ip_address, al.created_at
             FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id {where_clause} ORDER BY al.created_at DESC"""
    return fetch_paginated(sql, params, page, page_size)
