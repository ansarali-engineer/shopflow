"""Payment URL routes."""
from django.urls import path
from apps.payments.views import mock_process_payment, payment_webhook, payment_detail, order_payments, refund_view

urlpatterns = [
    path("mock-process/<int:payment_id>/", mock_process_payment),
    path("webhook/", payment_webhook),
    path("<int:payment_id>/", payment_detail),
    path("order/<int:order_id>/", order_payments),
    path("<int:payment_id>/refund/", refund_view),
]
