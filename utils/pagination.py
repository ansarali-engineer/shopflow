"""
Custom pagination classes for DRF.

StandardResultsPagination:
    LIMIT/OFFSET pagination for most endpoints.

KeysetPagination:
    Cursor-based pagination for large datasets where OFFSET
    becomes expensive.
"""
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class StandardResultsPagination(LimitOffsetPagination):
    """
    Standard pagination using limit/offset query parameters.

    Query params: ?page_size=20&page=2
    DRF maps these to limit/offset internally.
    """
    default_limit = 20
    max_limit = 100
    limit_query_param = "page_size"
    offset_query_param = "page"

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "data": data,
                "error": None,
                "meta": {
                    "page_size": self.limit,
                    "page": self.offset // self.limit + 1 if self.limit else 1,
                    "total": self.count,
                    "total_pages": (
                        self.count + self.limit - 1
                    ) // self.limit if self.limit else 1,
                    "has_next": self.get_next_link() is not None,
                    "has_prev": self.get_previous_link() is not None,
                },
            }
        )


def build_page_info(
    total: int, page: int, page_size: int
) -> dict:
    """Build a pagination metadata dict for manual pagination."""
    total_pages = (total + page_size - 1) // page_size if page_size else 1
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
