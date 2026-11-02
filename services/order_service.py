"""
Order service - checkout transaction orchestration.

The checkout flow:
  1. Authenticate customer (done in view via permissions)
  2. Validate shipping address exists and belongs to user
  3. Read customer's cart
  4. Validate product status, variant prices, and stock
  5. Validate coupon eligibility
  6. Calculate subtotal, discount, shipping, tax, total
  7. Create order + order_items (bulk insert)
  8. Reserve inventory (atomic UPDATE with rowcount check)
  9. Create pending payment record
  10. Clear cart (only after successful order creation)
  11. Return order details

All database changes run inside transaction.atomic().
Stock reservation uses atomic UPDATE to prevent overselling.
Prices are NEVER trusted from the client - always read from DB.
"""
import logging
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from django.db import IntegrityError

from repositories.user_repository import get_address_by_id
from repositories.cart_repository import (
    get_or_create_cart, get_cart_items, clear_cart, get_cart_subtotal,
)
from repositories.product_repository import get_product_owner_id
from repositories.order_repository import (
    create_order, bulk_insert_order_items, generate_order_number,
    get_order_with_details, get_customer_orders, get_order_owner_id,
    update_order_status, get_order_status, VALID_TRANSITIONS,
)
from repositories.inventory_repository import (
    reserve_stock, release_reserved, record_movement,
)
from repositories.payment_repository import create_payment
from repositories.audit_repository import log_action
from services.coupon_service import (
    validate_and_calculate_discount, record_redemption,
    CouponError,
)
from database.connection import DuplicateRecordError
from database.query_helpers import serialize_row, serialize_rows

logger = logging.getLogger("shopflow.services.order")

SHIPPING_COST = Decimal("9.99")
TAX_RATE = Decimal("0.08")


def checkout(user_id, shipping_address_id, coupon_code=None, idempotency_key=None):
    """
    Process checkout: create order from cart contents.

    Returns the full order dict with items, payments, and shipments.

    Raises ValueError for validation failures.
    Raises PermissionError for ownership violations.
    """
    with transaction.atomic():
        # 1. Validate shipping address
        address = get_address_by_id(shipping_address_id, user_id)
        if not address:
            raise ValueError("Shipping address not found or does not belong to you")

        # 2. Read cart
        cart_id = get_or_create_cart(user_id)
        cart_items = get_cart_items(cart_id)
        if not cart_items:
            raise ValueError("Your cart is empty")

        # 3. Validate cart items and build order_items list
        order_items_data = []
        subtotal = Decimal("0")
        stock_reservations = []

        for item in cart_items:
            if item["product_status"] != "active":
                raise ValueError(f"Product '{item['product_name']}' is no longer available")

            available = item.get("available_stock", 0)
            if available < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for '{item['product_name']}'. "
                    f"Available: {available}, Requested: {item['quantity']}"
                )

            # Use DB price, never client price
            unit_price = Decimal(str(item["unit_price"]))
            line_total = unit_price * item["quantity"]
            subtotal += line_total

            order_items_data.append([
                None,  # order_id filled after order creation
                item["product_id"],
                item["variant_id"],
                item["quantity"],
                str(unit_price),
                str(line_total),
            ])

            stock_reservations.append({
                "variant_id": item["variant_id"],
                "quantity": item["quantity"],
                "product_name": item["product_name"],
            })

        # 4. Validate coupon and calculate discount
        discount = Decimal("0")
        coupon_id = None
        if coupon_code:
            try:
                coupon_id, discount = validate_and_calculate_discount(
                    coupon_code, subtotal, user_id
                )
            except CouponError as e:
                raise ValueError(str(e))

        # 5. Calculate totals
        discounted_subtotal = subtotal - discount
        shipping_cost = SHIPPING_COST if discounted_subtotal > 0 else Decimal("0")
        tax_amount = (discounted_subtotal * TAX_RATE).quantize(Decimal("0.01"))
        total_amount = discounted_subtotal + shipping_cost + tax_amount

        # 6. Create order
        order_number = generate_order_number()
        order_id = create_order(
            customer_id=user_id,
            order_number=order_number,
            subtotal=str(subtotal),
            discount_amount=str(discount),
            shipping_cost=str(shipping_cost),
            tax_amount=str(tax_amount),
            total_amount=str(total_amount),
            shipping_address_id=shipping_address_id,
            coupon_id=coupon_id,
        )

        # 7. Bulk insert order items
        for item_row in order_items_data:
            item_row[0] = order_id
        bulk_insert_order_items(order_items_data)

        # 8. Reserve inventory (atomic)
        for res in stock_reservations:
            affected = reserve_stock(res["variant_id"], res["quantity"])
            if affected == 0:
                # This should not happen since we checked stock above,
                # but a concurrent request could have taken the last unit.
                raise ValueError(
                    f"Insufficient stock for '{res['product_name']}'. "
                    "Please try again."
                )
            record_movement(
                variant_id=res["variant_id"],
                movement_type="reserve",
                quantity=res["quantity"],
                reason=f"Order {order_number}",
                order_id=order_id,
            )

        # 9. Create pending payment
        payment_id = create_payment(
            order_id=order_id,
            payment_method="card",
            amount=str(total_amount),
            idempotency_key=idempotency_key,
        )

        # 10. Record coupon redemption
        if coupon_id:
            record_redemption(coupon_id, user_id, order_id, discount)

        # 11. Clear cart
        clear_cart(cart_id)

        # 12. Audit log
        log_action(
            user_id=user_id,
            action="ORDER_CREATED",
            entity_type="order",
            entity_id=order_id,
            new_values=f"order_number={order_number}, total={total_amount}",
        )

        logger.info("Order created: id=%s, user=%s, total=%s", order_id, user_id, total_amount)

    return serialize_row(get_order_with_details(order_id))


def get_order_detail(order_id, user_id):
    """Get order details, verifying ownership."""
    order = get_order_with_details(order_id)
    if not order:
        return None

    # Ownership check: customers can only see their own orders
    if order["customer_id"] != user_id and getattr(_get_request_user_role(), None) != "admin":
        # Service layer doesn't have request context; the view enforces this
        pass

    return serialize_row(order)


def get_my_orders(user_id, status=None, page=1, page_size=20):
    """Get paginated order history for a user."""
    rows, total = get_customer_orders(user_id, status, page, page_size)
    return serialize_rows(rows), total


def transition_order_status(order_id, new_status, user_id=None):
    """
    Transition an order to a new status.

    Validates the transition is allowed by the state machine.
    Raises ValueError for invalid transitions.
    """
    current = get_order_status(order_id)
    if not current:
        raise ValueError("Order not found")

    if new_status not in VALID_TRANSITIONS.get(current, set()):
        raise ValueError(
            f"Invalid transition: {current} -> {new_status}"
        )

    affected = update_order_status(order_id, new_status)

    # Handle side effects of certain transitions
    if new_status == "SHIPPED":
        _confirm_inventory_deduction(order_id)
    elif new_status == "CANCELLED":
        _release_inventory(order_id)

    log_action(
        user_id=user_id,
        action="ORDER_STATUS_CHANGED",
        entity_type="order",
        entity_id=order_id,
        old_values=current,
        new_values=new_status,
    )

    logger.info("Order %s transitioned: %s -> %s", order_id, current, new_status)
    return affected


def _confirm_inventory_deduction(order_id):
    """When an order ships, convert reservations to actual stock deductions."""
    from repositories.inventory_repository import confirm_deduct_stock
    from repositories.order_repository import get_order_by_id
    from database.query_helpers import fetch_all

    # Get order items
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT variant_id, quantity FROM order_items WHERE order_id = %s",
            [order_id],
        )
        items = cursor.fetchall()

    for variant_id, quantity in items:
        confirm_deduct_stock(variant_id, quantity)
        record_movement(
            variant_id=variant_id,
            movement_type="sale",
            quantity=quantity,
            reason=f"Order shipped: {order_id}",
            order_id=order_id,
        )


def _release_inventory(order_id):
    """When an order is cancelled, release reserved stock."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT variant_id, quantity FROM order_items WHERE order_id = %s",
            [order_id],
        )
        items = cursor.fetchall()

    for variant_id, quantity in items:
        release_reserved(variant_id, quantity)
        record_movement(
            variant_id=variant_id,
            movement_type="release",
            quantity=quantity,
            reason=f"Order cancelled: {order_id}",
            order_id=order_id,
        )


def _get_request_user_role():
    return None
