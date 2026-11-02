"""
User repository - all SQL for user account operations.
Every query uses parameterized statements. No ORM.
"""
import logging
from datetime import datetime

from django.contrib.auth.hashers import make_password, check_password
from django.db import connection, IntegrityError, transaction
from django.utils import timezone

from database.query_helpers import (
    fetch_one, fetch_all, fetch_scalar,
    insert_one, update_or_delete, serialize_row,
)
from database.connection import DuplicateRecordError

logger = logging.getLogger("shopflow.repositories.user")


def _user_select() -> str:
    return (
        "SELECT id, email, password_hash, first_name, last_name, "
        "phone, role, status, created_at, updated_at FROM users "
    )


def create_user(email, password, first_name, last_name, role="customer", phone=None):
    sql = """INSERT INTO users (email, password_hash, first_name, last_name, phone, role, status)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    hashed = make_password(password)
    user_id = insert_one(sql, [email.lower().strip(), hashed, first_name, last_name, phone, role, "active"])
    user = get_user_by_id(user_id)
    if user:
        user.pop("password_hash", None)
    return user


def get_user_by_id(user_id):
    return fetch_one(_user_select() + "WHERE id = %s", [user_id])


def get_user_by_email(email):
    return fetch_one(_user_select() + "WHERE email = %s", [email.lower().strip()])


def list_admin_users(page=1, page_size=20, role=None, status=None, search=None):
    """Return one filtered page of users and the total matching count."""
    filters, params = [], []
    if role:
        filters.append("role = %s")
        params.append(role)
    if status:
        filters.append("status = %s")
        params.append(status)
    if search:
        filters.append(
            "(email LIKE %s OR first_name LIKE %s OR last_name LIKE %s)"
        )
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    total = fetch_scalar(
        f"SELECT COUNT(*) FROM users{where_clause}", params
    )
    offset = (page - 1) * page_size
    users = fetch_all(
        "SELECT id, email, first_name, last_name, phone, role, status, "
        "created_at, updated_at FROM users"
        f"{where_clause} ORDER BY id ASC LIMIT %s OFFSET %s",
        [*params, page_size, offset],
    )
    return users, total


def update_admin_user(user_id, updates):
    """Update an allowlisted set of account fields for admin management."""
    allowed_fields = {
        "email", "first_name", "last_name", "phone", "role", "status",
    }
    sets, params = [], []
    for field, value in updates.items():
        if field in allowed_fields:
            sets.append(f"{field} = %s")
            params.append(value)
    if not sets:
        return 0

    sets.append("updated_at = %s")
    params.extend([timezone.now(), user_id])
    sql = f"UPDATE users SET {', '.join(sets)} WHERE id = %s"
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.rowcount
    except IntegrityError as exc:
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            raise DuplicateRecordError(str(exc)) from exc
        raise


def verify_password(user, password):
    stored = user.get("password_hash")
    if not stored:
        return False
    return check_password(password, stored)


def update_user_profile(user_id, first_name=None, last_name=None, phone=None):
    sets, params = [], []
    if first_name is not None: sets.append("first_name = %s"); params.append(first_name)
    if last_name is not None: sets.append("last_name = %s"); params.append(last_name)
    if phone is not None: sets.append("phone = %s"); params.append(phone)
    if not sets: return 0
    sets.append("updated_at = %s"); params.append(datetime.utcnow()); params.append(user_id)
    sql = f"UPDATE users SET {', '.join(sets)} WHERE id = %s"
    return update_or_delete(sql, params)


def update_user_status(user_id, status):
    return update_or_delete("UPDATE users SET status = %s, updated_at = %s WHERE id = %s",
                           [status, datetime.utcnow(), user_id])


def get_user_profile(user_id):
    sql = """SELECT u.id, u.email, u.first_name, u.last_name, u.phone, u.role, u.status, u.created_at,
             (SELECT COUNT(*) FROM addresses a WHERE a.user_id = u.id) AS address_count,
             (SELECT COUNT(*) FROM orders o WHERE o.customer_id = u.id) AS order_count,
             (SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) FROM order_items oi
              JOIN orders o2 ON o2.id = oi.order_id WHERE o2.customer_id = u.id
                AND o2.status NOT IN ('CANCELLED','REFUNDED')) AS total_spent
             FROM users u WHERE u.id = %s"""
    return fetch_one(sql, [user_id])


def create_address(user_id, label, street_line1, street_line2=None, city="", state="",
                   postal_code="", country="US", is_default=False):
    if is_default:
        update_or_delete("UPDATE addresses SET is_default = FALSE WHERE user_id = %s", [user_id])
    sql = """INSERT INTO addresses (user_id, label, street_line1, street_line2, city, state, postal_code, country, is_default)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    return insert_one(sql, [user_id, label, street_line1, street_line2, city, state, postal_code, country, is_default])


def get_addresses_by_user(user_id):
    sql = """SELECT id, user_id, label, street_line1, street_line2, city, state, postal_code, country, is_default, created_at, updated_at
             FROM addresses WHERE user_id = %s ORDER BY is_default DESC, created_at ASC"""
    return fetch_all(sql, [user_id])


def get_address_by_id(address_id, user_id):
    sql = """SELECT id, user_id, label, street_line1, street_line2, city, state, postal_code, country, is_default, created_at, updated_at
             FROM addresses WHERE id = %s AND user_id = %s"""
    return fetch_one(sql, [address_id, user_id])


def update_address(address_id, user_id, **kwargs):
    sets, params = [], []
    for col, val in kwargs.items():
        if val is not None:
            sets.append(f"{col} = %s"); params.append(val)
    if not sets: return 0
    sets.append("updated_at = %s"); params.append(datetime.utcnow())
    params.extend([address_id, user_id])
    sql = f"UPDATE addresses SET {', '.join(sets)} WHERE id = %s AND user_id = %s"
    return update_or_delete(sql, params)


def delete_address(address_id, user_id):
    return update_or_delete("DELETE FROM addresses WHERE id = %s AND user_id = %s", [address_id, user_id])


def authenticate_user(email, password):
    user = get_user_by_email(email)
    if user is None:
        check_password(password, make_password("dummy"))
        return None
    if not verify_password(user, password): return None
    if user.get("status") != "active": return None
    return user


def update_password(user_id, new_password):
    return update_or_delete("UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s",
                           [make_password(new_password), datetime.utcnow(), user_id])
