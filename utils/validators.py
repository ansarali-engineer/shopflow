"""
Input validation helpers used across serializers and services.

These keep validation logic out of SQL and in the Python layer
where it belongs.
"""
from decimal import Decimal, InvalidOperation


def validate_positive_decimal(value, field_name="amount") -> Decimal:
    """Validate that a value is a positive decimal number."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid number")

    if d < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return d


def validate_quantity(value: int) -> int:
    """Validate that a quantity is a positive integer."""
    try:
        q = int(value)
    except (ValueError, TypeError):
        raise ValueError("Quantity must be an integer")

    if q < 1:
        raise ValueError("Quantity must be at least 1")
    return q


def validate_pagination_params(
    page: int, page_size: int, max_size: int = 100
) -> tuple[int, int]:
    """Clamp pagination parameters to safe bounds."""
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 20), max_size))
    return page, page_size


def validate_email(email: str) -> str:
    """Basic email format validation."""
    if not email or "@" not in email:
        raise ValueError("A valid email address is required")
    return email.strip().lower()


def validate_password(password: str) -> str:
    """
    Validate password strength.
    Minimum 8 chars, at least one letter and one digit.
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not has_letter or not has_digit:
        raise ValueError(
            "Password must contain at least one letter and one digit"
        )

    return password


def validate_order_status_transition(
    current: str, target: str
) -> bool:
    """
    Validate that an order status transition is allowed.

    Valid transitions:
        PENDING_PAYMENT → PAID
        PENDING_PAYMENT → CANCELLED
        PAID → PROCESSING
        PAID → CANCELLED (with refund)
        PROCESSING → SHIPPED
        SHIPPED → DELIVERED
        PAID → REFUNDED
        PROCESSING → REFUNDED
        DELIVERED → RETURNED (with refund)
    """
    VALID_TRANSITIONS = {
        "PENDING_PAYMENT": {"PAID", "CANCELLED"},
        "PAID": {"PROCESSING", "CANCELLED", "REFUNDED"},
        "PROCESSING": {"SHIPPED", "REFUNDED"},
        "SHIPPED": {"DELIVERED"},
        "DELIVERED": {"RETURNED"},
    }

    if current not in VALID_TRANSITIONS:
        return False

    return target in VALID_TRANSITIONS[current]
