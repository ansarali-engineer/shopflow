"""Review API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from repositories.review_repository import (
    create_review, get_product_reviews, has_user_reviewed_product,
)
from permissions.role_permissions import IsCustomerOrAdmin
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
    return paginated_response(rows, total, page, page_size)
