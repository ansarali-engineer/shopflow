"""
Coupon service - discount validation and calculation.

Business rules:
  - Check expiry date
  - Check minimum order amount
  - Check total redemption limit
  - Check per-customer redemption limit
  - Apply max discount cap
  - Calculate percentage or fixed discount
"""
import logging
from decimal import Decimal
from datetime import datetime

from django.utils import timezone

from repositories.coupon_repository import (
    get_coupon_by_code, get_coupon_redemption_count,
    get_customer_coupon_redemption_count, redeem_coupon,
)
from database.connection import DuplicateRecordError

logger = logging.getLogger("shopflow.services.coupon")


class CouponError(Exception):
    pass


class CouponExpiredError(CouponError):
    pass


class CouponLimitExceededError(CouponError):
    pass


class CouponNotEligibleError(CouponError):
    pass


def validate_and_calculate_discount(code, subtotal, user_id):
    """
    Validate a coupon and return the discount amount as a Decimal.

    Raises CouponError subclasses if invalid.
    Returns (coupon_id, discount_amount).
    """
    coupon = get_coupon_by_code(code)
    if not coupon:
        raise CouponError("Coupon not found or inactive")

    # Use timezone-aware now; make coupon datetimes comparable by stripping tz
    # if the DB returns naive datetimes (MySQL without tz config).
    now = timezone.now()

    def _to_naive(dt):
        """Convert aware dt to naive UTC if needed for comparison."""
        if dt is None:
            return None
        if timezone.is_aware(dt):
            return dt.replace(tzinfo=None)
        return dt

    now_naive = now.replace(tzinfo=None)

    # Check expiry
    valid_until = _to_naive(coupon.get("valid_until"))
    if valid_until and valid_until < now_naive:
        raise CouponExpiredError("Coupon has expired")

    valid_from = _to_naive(coupon.get("valid_from"))
    if valid_from and valid_from > now_naive:
        raise CouponNotEligibleError("Coupon is not yet valid")

    # Check minimum order amount
    subtotal_dec = Decimal(str(subtotal))
    min_amount = Decimal(str(coupon.get("min_order_amount") or 0))
    if subtotal_dec < min_amount:
        raise CouponNotEligibleError(
            f"Minimum order amount of {min_amount} required"
        )

    # Check total redemption limit
    if coupon.get("max_redemptions"):
        total = get_coupon_redemption_count(coupon["id"])
        if total >= coupon["max_redemptions"]:
            raise CouponLimitExceededError("Coupon redemption limit reached")

    # Check per-customer limit
    if coupon.get("per_customer_limit"):
        customer_count = get_customer_coupon_redemption_count(coupon["id"], user_id)
        if customer_count >= coupon["per_customer_limit"]:
            raise CouponLimitExceededError("You have already used this coupon the maximum number of times")

    # Calculate discount
    discount_value = Decimal(str(coupon["discount_value"]))

    if coupon["discount_type"] == "percentage":
        discount = (subtotal_dec * discount_value / Decimal("100"))
        # Apply max discount cap
        if coupon.get("max_discount_amount"):
            max_cap = Decimal(str(coupon["max_discount_amount"]))
            discount = min(discount, max_cap)
    elif coupon["discount_type"] == "fixed":
        discount = min(discount_value, subtotal_dec)
    else:
        raise CouponError(f"Unknown discount type: {coupon['discount_type']}")

    logger.info("Coupon applied: code=%s, discount=%s", code, discount)
    return coupon["id"], discount


def record_redemption(coupon_id, user_id, order_id, discount_amount):
    """Record a coupon redemption after order creation."""
    return redeem_coupon(coupon_id, user_id, order_id, str(discount_amount))
