"""Payment API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from utils.responses import success_response, error_response
from services.payment_service import process_mock_payment, handle_payment_webhook, refund_payment
from repositories.payment_repository import get_payment_by_id, get_payments_by_order
from database.query_helpers import serialize_row, serialize_rows


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mock_process_payment(request, payment_id):
    """POST /api/v1/payments/mock-process/{id}/"""
    success = request.data.get("success", True)
    try:
        result = process_mock_payment(payment_id, success=success)
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    return success_response(result)


@api_view(["POST"])
@permission_classes([AllowAny])
def payment_webhook(request):
    """POST /api/v1/payments/webhook/"""
    data = request.data
    if not data.get("transaction_ref") or not data.get("status"):
        return error_response("transaction_ref and status are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    try:
        result = handle_payment_webhook(
            transaction_ref=data["transaction_ref"],
            status=data["status"],
            order_id=data.get("order_id"),
        )
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    return success_response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_detail(request, payment_id):
    """GET /api/v1/payments/{id}/"""
    payment = get_payment_by_id(payment_id)
    if not payment:
        return error_response("Payment not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(serialize_row(payment))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_payments(request, order_id):
    """GET /api/v1/payments/order/{order_id}/"""
    payments = get_payments_by_order(order_id)
    return success_response(serialize_rows(payments))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refund_view(request, payment_id):
    """POST /api/v1/payments/{id}/refund/"""
    reason = request.data.get("reason", "Customer requested refund")
    try:
        result = refund_payment(payment_id, reason)
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    return success_response(result)
