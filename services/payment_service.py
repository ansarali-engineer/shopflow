"""
Payment service - mock payment processing with idempotency.

Key patterns:
  - Idempotency via unique constraint on idempotency_key
  - Duplicate callback detection via transaction_ref
  - Payment status validation
  - Order status updates on payment success
  - Inventory confirmation on ship, release on cancel/refund
"""
import logging
import uuid
from datetime import datetime

from django.db import transaction

from repositories.payment_repository import (
    create_payment, get_payment_by_id, get_payment_by_idempotency_key,
    update_payment_status, check_duplicate_callback,
)
from repositories.order_repository import (
    get_order_by_id, update_order_status, get_order_status,
)
from repositories.inventory_repository import (
    release_reserved, record_movement,
)
from repositories.audit_repository import log_action
from database.connection import DuplicateRecordError
from database.query_helpers import serialize_row

logger = logging.getLogger("shopflow.services.payment")


def process_mock_payment(payment_id, success=True):
    """
    Simulate payment processing for a pending payment.

    In production, this would call an external payment gateway.
    Here we simulate success/failure with a random transaction reference.

    Idempotency: if the payment is already processed (not pending),
    return the current state without re-processing.
    """
    with transaction.atomic():
        payment = get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")

        # Idempotency check: already processed
        if payment["status"] != "pending":
            logger.info("Payment %s already processed: %s", payment_id, payment["status"])
            return serialize_row(payment)

        order = get_order_by_id(payment["order_id"])
        if not order:
            raise ValueError("Order not found for this payment")

        if success:
            transaction_ref = f"MOCK-{uuid.uuid4().hex[:16].upper()}"
            update_payment_status(
                payment_id,
                status="success",
                transaction_ref=transaction_ref,
            )
            # Update order to PAID
            update_order_status(order["id"], "PAID")
            log_action(
                user_id=order["customer_id"],
                action="PAYMENT_SUCCESS",
                entity_type="payment",
                entity_id=payment_id,
                new_values=f"transaction_ref={transaction_ref}",
            )
            logger.info("Payment succeeded: payment_id=%s, order=%s", payment_id, order["id"])
        else:
            failure_reason = "Simulated payment failure"
            update_payment_status(
                payment_id,
                status="failed",
                failure_reason=failure_reason,
            )
            log_action(
                user_id=order["customer_id"],
                action="PAYMENT_FAILED",
                entity_type="payment",
                entity_id=payment_id,
                new_values=failure_reason,
            )
            logger.info("Payment failed: payment_id=%s", payment_id)

    return serialize_row(get_payment_by_id(payment_id))


def handle_payment_webhook(transaction_ref, status, order_id=None):
    """
    Handle a payment gateway webhook callback.

    Idempotency: if we already processed this transaction_ref,
    return the existing payment without re-processing.
    """
    # Check for duplicate callback
    existing = check_duplicate_callback(transaction_ref)
    if existing:
        logger.info("Duplicate webhook for transaction_ref=%s, ignoring", transaction_ref)
        return serialize_row(existing)

    # Find the payment by order_id (in real systems, match by transaction_ref)
    if not order_id:
        raise ValueError("order_id required for webhook processing")

    from repositories.payment_repository import get_payments_by_order
    payments = get_payments_by_order(order_id)
    pending_payment = None
    for p in payments:
        if p["status"] == "pending":
            pending_payment = p
            break

    if not pending_payment:
        raise ValueError("No pending payment found for this order")

    with transaction.atomic():
        if status == "success":
            update_payment_status(
                pending_payment["id"],
                status="success",
                transaction_ref=transaction_ref,
            )
            update_order_status(order_id, "PAID")
        else:
            update_payment_status(
                pending_payment["id"],
                status="failed",
                failure_reason="Webhook reported failure",
            )

        log_action(
            user_id=None,
            action="PAYMENT_WEBHOOK",
            entity_type="payment",
            entity_id=pending_payment["id"],
            new_values=f"transaction_ref={transaction_ref}, status={status}",
        )

    return serialize_row(get_payment_by_id(pending_payment["id"]))


def refund_payment(payment_id, reason="Customer requested refund"):
    """Process a refund for a completed payment."""
    with transaction.atomic():
        payment = get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")

        if payment["status"] != "success":
            raise ValueError("Can only refund successful payments")

        # Create refund record (negative payment)
        update_payment_status(payment_id, status="refunded")

        # Update order status
        order = get_order_by_id(payment["order_id"])
        if order:
            update_order_status(order["id"], "REFUNDED")
            # Release inventory
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT variant_id, quantity FROM order_items WHERE order_id = %s",
                    [order["id"]],
                )
                items = cursor.fetchall()

            for variant_id, quantity in items:
                release_reserved(variant_id, quantity)
                record_movement(
                    variant_id=variant_id,
                    movement_type="release",
                    quantity=quantity,
                    reason=f"Refund: {reason}",
                    order_id=order["id"],
                )

        log_action(
            user_id=None,
            action="PAYMENT_REFUNDED",
            entity_type="payment",
            entity_id=payment_id,
            new_values=f"reason={reason}",
        )
        logger.info("Payment refunded: payment_id=%s, reason=%s", payment_id, reason)

    return serialize_row(get_payment_by_id(payment_id))
