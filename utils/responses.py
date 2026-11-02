"""
Consistent API response helpers.

All endpoints return:
{
    "success": true/false,
    "data": { ... } or [ ... ] or null,
    "error": { ... } or null,
    "meta": { ... } or null  # pagination, counts, etc.
}
"""
from rest_framework.response import Response
from rest_framework import status as http_status


def success_response(
    data=None,
    status=http_status.HTTP_200_OK,
    meta=None,
):
    """Return a success response with data and optional metadata."""
    return Response(
        {
            "success": True,
            "data": data,
            ""
            "error": None,
            **({"meta": meta} if meta else {}),
        },
        status=status,
    )

def error_response(
    message: str,
    code: str = "ERROR",
    status: int = http_status.HTTP_400_BAD_REQUEST,
    details=None,
):
    """Return an error response with a consistent structure."""
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response(
        {
            "success": False,
            "data": None,
            "error": error,
        },
        status=status,
    )



def paginated_response(rows, total, page, page_size, base_url=""):
    """Return a paginated list response with metadata."""
    total_pages = (total + page_size - 1) // page_size
    return Response(
        {
            "success": True,
            "data": rows,
            "error": None,
            "meta": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
        status=http_status.HTTP_200_OK,
    )


def created_response(data=None, location=None):
    """Return a 201 Created response."""
    return success_response(data, status=http_status.HTTP_201_CREATED)


def no_content_response():
    """Return a 204 No Content response."""
    return Response(status=http_status.HTTP_204_NO_CONTENT)
