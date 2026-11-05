"""Review API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from repositories.review_repository import (
    create_review, get_product_reviews, has_user_reviewed_product,
    get_review_by_id, update_review_status, has_purchased_product,
)
from permissions.role_permissions import IsCustomerOrAdmin, IsAdmin
from database.query_helpers import serialize_rows, serialize_row


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsCustomerOrAdmin])
def create_review_view(request):
    """POST /api/v1/reviews/"""
    data = request.data
    if not data.get("product_id") or not data.get("rating") or not data.get("title"):
        return error_response("product_id, rating, and title are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    rating = int(data["rating"])
    if rating < 1 or rating > 5:
        return error_response("Rating must be between 1 and 5",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)

    if has_user_reviewed_product(data["product_id"], request.user.id):
        return error_response("You have already reviewed this product",
                              "VALIDATION_ERROR", status=status.HTTP_409_CONFLICT)

    # Enforce verified-purchase: customer must have a DELIVERED order for this product
    if request.user.role == "customer" and not has_purchased_product(request.user.id, data["product_id"]):
        return error_response(
            "You can only review products you have purchased and received",
            "PERMISSION_DENIED", status=status.HTTP_403_FORBIDDEN,
        )

    review_id = create_review(
        product_id=data["product_id"],
        user_id=request.user.id,
        rating=rating,
        title=data["title"],
        body=data.get("body", ""),
    )
    return success_response({"review_id": review_id}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def product_reviews(request, product_id):
    """GET /api/v1/reviews/product/{product_id}/"""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    rows, total = get_product_reviews(
        product_id,
        rating=request.GET.get("rating"),
        page=page, page_size=page_size,
    )
    # Attach eligibility for authenticated customers
    can_review = False
    already_reviewed = False
    if request.user and getattr(request.user, "is_authenticated", False) and request.user.role == "customer":
        already_reviewed = has_user_reviewed_product(product_id, request.user.id)
        can_review = (not already_reviewed) and has_purchased_product(request.user.id, product_id)

    from utils.responses import paginated_response as _pr
    from rest_framework.response import Response
    total_pages = (total + page_size - 1) // page_size
    return Response({
        "success": True,
        "data": rows,
        "error": None,
        "meta": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "can_review": can_review,
        "already_reviewed": already_reviewed,
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdmin])
def moderate_review(request, review_id):
    """PATCH /api/v1/reviews/{id}/moderate/ — admin sets status to published/hidden/flagged."""
    new_status = request.data.get("status")
    if new_status not in ("published", "hidden", "flagged"):
        return error_response(
            "status must be published, hidden, or flagged",
            "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST,
        )
    review = get_review_by_id(review_id)
    if not review:
        return error_response("Review not found", "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
    update_review_status(review_id, new_status)
    updated = get_review_by_id(review_id)
    return success_response(serialize_row(updated))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def all_reviews(request):
    """GET /api/v1/reviews/ — admin gets all reviews with optional status filter."""
    from repositories.review_repository import get_product_reviews
    from database.query_helpers import fetch_all, fetch_paginated
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    review_status = request.GET.get("status")
    conditions = []
    params = []
    if review_status:
        conditions.append("r.status = %s")
        params.append(review_status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""SELECT r.id, r.product_id, r.user_id, r.rating, r.title, r.body, r.status, r.created_at,
             u.first_name AS reviewer_first_name, u.last_name AS reviewer_last_name,
             p.name AS product_name
             FROM reviews r
             INNER JOIN users u ON r.user_id = u.id
             INNER JOIN products p ON r.product_id = p.id
             {where} ORDER BY r.created_at DESC"""
    rows, total = fetch_paginated(sql, params, page, page_size)
    return paginated_response(rows, total, page, page_size)
