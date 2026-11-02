"""
Custom DRF exception handler.

Returns a consistent JSON error format:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": { ... }  # optional field-level errors
    }
}

Never exposes SQL statements, stack traces, or internal paths.
"""
import logging

from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger("shopflow.exceptions")


def shopflow_exception_handler(exc, context):
    """
    Custom exception handler that wraps all errors in a
    consistent response structure.
    """
    # Let DRF handle the base conversion first
    response = drf_default_handler(exc, context)

    if response is None:
        # Unhandled exception — return generic 500
        logger.error(
            "Unhandled exception: %s — %s",
            type(exc).__name__,
            str(exc)[:200],  # truncate to avoid leaking internals
            exc_info=True,
        )
        return Response(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                },
            },
            status=500,
        )

    # Map known exception types to error codes
    error_code = "ERROR"
    error_details = None

    if isinstance(exc, ValidationError):
        error_code = "VALIDATION_ERROR"
        error_details = (
            exc.detail if isinstance(exc.detail, list) else
            {k: str(v) for k, v in exc.detail.items()}
            if isinstance(exc.detail, dict) else
            str(exc.detail)
        )
    elif isinstance(exc, AuthenticationFailed):
        error_code = "AUTHENTICATION_FAILED"
    elif isinstance(exc, NotAuthenticated):
        error_code = "NOT_AUTHENTICATED"
    elif isinstance(exc, PermissionDenied):
        error_code = "PERMISSION_DENIED"
    elif isinstance(exc, APIException):
        error_code = getattr(exc, "code", "API_ERROR")
    elif hasattr(exc, "code"):
        error_code = exc.code

    # Override the response data with our format
    response.data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": _safe_message(exc),
            **({"details": error_details} if error_details else {}),
        },
    }

    return response


def _safe_message(exc) -> str:
    """Extract a safe, user-facing message from an exception."""
    if isinstance(exc, ValidationError):
        if isinstance(exc.detail, list):
            return "; ".join(str(d) for d in exc.detail)
        if isinstance(exc.detail, dict):
            return "Validation failed for one or more fields."
        return str(exc.detail)

    return str(exc) if str(exc) else "An error occurred."
