"""
Reusable query helpers that map raw SQL tuples to dicts.

These are the building blocks every repository uses. They handle:
- cursor.description → column names
- fetchone / fetchall → dict / list[dict]
- INSERT ... RETURNING lastrowid
- Pagination (LIMIT/OFFSET and keyset)
- Decimal and datetime serialization
- NULL values
- Safe sort-column allowlists
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from django.db import connection

logger = logging.getLogger("shopflow.database")


# ── Serialization helpers ──────────────────────────────────

def serialize_value(value: Any) -> Any:
    """Convert a single DB value to a JSON-serializable type."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        # Keep precision: return as string to avoid float rounding
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_row(row: dict) -> dict:
    """Serialize all values in a dict row for JSON output."""
    return {k: serialize_value(v) for k, v in row.items()}


def serialize_rows(rows: list[dict]) -> list[dict]:
    """Serialize a list of dict rows for JSON output."""
    return [serialize_row(r) for r in rows]


# ── Column mapping ────────────────────────────────────────

def _columns_from_cursor(cursor) -> list[str]:
    """Extract column names from cursor.description."""
    if cursor.description is None:
        return []
    return [col[0] for col in cursor.description]


def _row_to_dict(row: tuple, columns: list[str]) -> dict:
    """Map a tuple row to a dict using column names."""
    return dict(zip(columns, row))


# ── Read helpers ───────────────────────────────────────────

def fetch_one(sql: str, params: list | None = None) -> dict | None:
    """
    Execute a query and return a single row as a dict, or None.

    Example:
        user = fetch_one(
            "SELECT id, email FROM users WHERE id = %s", [user_id]
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        columns = _columns_from_cursor(cursor)
        return _row_to_dict(row, columns)


def fetch_all(
    sql: str, params: list | None = None
) -> list[dict]:
    """
    Execute a query and return all rows as a list of dicts.

    For large result sets, consider fetch_paginated instead to
    avoid loading everything into memory.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        rows = cursor.fetchall()
        columns = _columns_from_cursor(cursor)
        return [_row_to_dict(row, columns) for row in rows]


def fetch_scalar(
    sql: str, params: list | None = None
) -> Any:
    """
    Execute a query and return a single scalar value.

    Example:
        count = fetch_scalar(
            "SELECT COUNT(*) FROM products WHERE status = %s", ["active"]
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]


def fetch_column(
    sql: str, params: list | None = None
) -> list[Any]:
    """
    Execute a query and return the first column of every row.

    Example:
        ids = fetch_column(
            "SELECT id FROM products WHERE seller_id = %s", [seller_id]
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        rows = cursor.fetchall()
        return [row[0] for row in rows]


# ── Write helpers ──────────────────────────────────────────

def insert_one(
    sql: str, params: list | None = None
) -> int:
    """
    Execute an INSERT and return the new auto-increment ID.

    Uses cursor.lastrowid, which MySQL provides after INSERT.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.lastrowid


def insert_many(
    sql: str, rows: list[list] | None = None
) -> int:
    """
    Execute a bulk INSERT using executemany().

    Returns the total number of affected rows.
    """
    if not rows:
        return 0
    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)
        return cursor.rowcount


def update_or_delete(
    sql: str, params: list | None = None
) -> int:
    """
    Execute an UPDATE or DELETE and return the number of affected rows.

    Example:
        affected = update_or_delete(
            "UPDATE products SET status = %s WHERE id = %s",
            ["inactive", product_id],
        )
        if affected == 0:
            raise RecordNotFoundError("Product not found")
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.rowcount


# ── Pagination helpers ────────────────────────────────────

def fetch_paginated(
    sql: str,
    params: list | None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    Fetch a page of results plus the total count.

    Returns (rows, total_count).

    Uses LIMIT/OFFSET pagination. For large datasets with stable
    sorting, prefer keyset pagination (fetch_keyset_paginated).
    """
    offset = (page - 1) * page_size
    limit = page_size

    paginated_sql = f"{sql} LIMIT %s OFFSET %s"
    paginated_params = (params or []) + [limit, offset]

    rows = fetch_all(paginated_sql, paginated_params)

    # Get total count by wrapping the SQL in a COUNT subquery
    count_sql = f"SELECT COUNT(*) FROM ({sql}) AS _count_subq"
    total = fetch_scalar(count_sql, params)

    return rows, total


def fetch_keyset_paginated(
    sql: str,
    params: list | None,
    last_id: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """
    Keyset (seek) pagination — more efficient than OFFSET for large tables.

    The SQL must end with an ORDER BY id ASC so we can add
    WHERE id > %s before the ORDER BY.

    Returns (rows, next_cursor_id). When next_cursor_id is 0,
    there are no more pages.
    """
    # Inject WHERE id > %s before ORDER BY
    if "ORDER BY" not in sql.upper():
        raise ValueError("SQL must contain ORDER BY for keyset pagination")

    parts = sql.rsplit("ORDER BY", 1)
    keyset_sql = (
        f"{parts[0]} AND id > %s ORDER BY{parts[1]} LIMIT %s"
        if "WHERE" in parts[0].upper()
        else f"{parts[0]} WHERE id > %s ORDER BY{parts[1]} LIMIT %s"
    )
    keyset_params = (params or []) + [last_id, limit]

    rows = fetch_all(keyset_sql, keyset_params)
    next_cursor = rows[-1]["id"] if rows and len(rows) == limit else 0

    return rows, next_cursor


# ── Safe sort column allowlist ────────────────────────────

def safe_sort_fragment(
    sort_param: str | None,
    allowlist: dict[str, str],
    default: str = "id",
) -> str:
    """
    Return a safe ORDER BY fragment from user-supplied sort parameter.

    Column names cannot be parameterized in SQL — they are identifiers,
    not values. So we map the user's sort key to a trusted SQL fragment
    from an allowlist dict.

    Example:
        SORT_COLUMNS = {
            "price_asc": "price ASC",
            "price_desc": "price DESC",
            "newest": "created_at DESC",
            "name_asc": "name ASC",
        }
        order_by = safe_sort_fragment(
            request.GET.get("sort"), SORT_COLUMNS
        )
        sql = f"SELECT * FROM products ORDER BY {order_by}"
    """
    if not sort_param or sort_param not in allowlist:
        return allowlist.get(default, "id ASC")
    return allowlist[sort_param]


# ── Transaction helper ────────────────────────────────────

def execute_in_transaction(
    sql: str, params: list | None = None
) -> int:
    """
    Execute a write statement inside a transaction.

    Use this for single statements that need explicit commit.
    For multi-statement transactions, use transaction.atomic()
    in your service layer.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.rowcount
