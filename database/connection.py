"""
Low-level database connection utilities.

Provides a context-managed cursor that:
- Opens a cursor from Django's connection
- Commits on success, rolls back on exception
- Maps Django's internal IntegrityError to our DuplicateRecordError
- Logs SQL errors without exposing query text in responses
"""
import logging
from contextlib import contextmanager
from typing import Any, Generator

from django.db import connection, IntegrityError, transaction

logger = logging.getLogger("shopflow.database")


class DuplicateRecordError(IntegrityError):
    """Raised when a UNIQUE constraint is violated."""
    pass


class RecordNotFoundError(Exception):
    """Raised when a required row is not found."""
    pass


@contextmanager
def get_cursor() -> Generator[Any, None, None]:
    """
    Context manager yielding a database cursor.

    Automatically commits on success, rolls back on failure.
    Translates IntegrityError into DuplicateRecordError for
    cleaner handling in service-layer code.
    """
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except IntegrityError as exc:
        connection.rollback()
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg:
            logger.warning("Duplicate record: %s", type(exc).__name__)
            raise DuplicateRecordError(str(exc)) from exc
        logger.error("Database integrity error: %s", type(exc).__name__)
        raise
    except Exception:
        connection.rollback()
        logger.error("Database error, transaction rolled back")
        raise
    finally:
        cursor.close()


@contextmanager
def transactional_cursor() -> Generator[Any, None, None]:
    """
    Context manager for explicit transaction control.

    Use this when you need to run multiple statements that must
    all succeed or all fail together, but without using
    transaction.atomic() (e.g. when you need SELECT ... FOR UPDATE).
    """
    cursor = connection.cursor()
    try:
        # Disable autocommit for explicit transaction
        connection.set_autocommit(False)
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        logger.error("Transaction failed, rolled back")
        raise
    finally:
        connection.set_autocommit(True)
        cursor.close()


def raw_execute(sql: str, params: list | None = None) -> int:
    """
    Execute a write statement and return affected row count.

    Does NOT auto-commit; use inside transaction.atomic() or
    get_cursor() for commit handling.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.rowcount


def raw_fetchone(sql: str, params: list | None = None) -> tuple | None:
    """Execute a read query and return a single row tuple, or None."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchone()


def raw_fetchall(sql: str, params: list | None = None) -> list[tuple]:
    """Execute a read query and return all rows as a list of tuples."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchall()
