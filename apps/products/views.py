"""Product catalog API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from utils.validators import validate_pagination_params
from database.query_helpers import serialize_row, serialize_rows
from services.product_service import (
    get_catalog_product, search_products, get_categories,
    get_category_descendants, seller_create_product, seller_update_product,
    get_seller_catalog, get_top_products_by_category,
    get_products_above_avg_price, get_unsold_products,
)
from permissions.role_permissions import IsSellerOrAdmin, IsSellerOwnerOrAdmin
from repositories.product_repository import (
    create_product_variant, add_product_image, get_product_owner_id,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def product_list(request):
    """GET /api/v1/products/ - catalog with search, filter, sort, pagination."""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    rows, total = search_products(
        search=request.GET.get("search"),
        category_id=request.GET.get("category_id"),
        min_price=request.GET.get("min_price"),
        max_price=request.GET.get("max_price"),
        seller_id=request.GET.get("seller_id"),
        min_rating=request.GET.get("min_rating"),
        in_stock=request.GET.get("in_stock") == "true",
        sort=request.GET.get("sort"),
        page=page, page_size=page_size,
    )
    return paginated_response(rows, total, page, page_size)


@api_view(["GET"])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """GET /api/v1/products/{id_or_slug}/ - accepts numeric id or slug."""
    from database.query_helpers import fetch_scalar
    # If the route captured a string slug (non-numeric), resolve to id first
    if not str(product_id).isdigit():
        resolved = fetch_scalar(
            "SELECT id FROM products WHERE slug = %s AND status = 'active'",
            [product_id],
        )
        if not resolved:
            return error_response("Product not found", "NOT_FOUND",
                                  status=status.HTTP_404_NOT_FOUND)
        product_id = resolved
    product = get_catalog_product(product_id)
    if not product:
        return error_response("Product not found", "NOT_FOUND",
                              status=status.HTTP_404_NOT_FOUND)
    return success_response(product)


@api_view(["GET"])
@permission_classes([AllowAny])
def category_tree(request):
    """GET /api/v1/products/categories/ - hierarchical category tree."""
    tree = get_categories()
    return success_response(tree)


@api_view(["GET"])
@permission_classes([AllowAny])
def category_subtree(request, slug):
    """GET /api/v1/products/categories/{slug}/ - category with descendants."""
    from repositories.product_repository import fetch_one
    from database.query_helpers import fetch_one as fh
    cat = fh("SELECT id, name, slug FROM categories WHERE slug = %s", [slug])
    if not cat:
        return error_response("Category not found", "NOT_FOUND",
                                status=status.HTTP_404_NOT_FOUND)
    descendants = get_category_descendants(cat["id"])
    return success_response({"category": serialize_row(cat), "descendants": descendants})


@api_view(["GET"])
@permission_classes([AllowAny])
def top_products_per_category(request):
    """GET /api/v1/products/top-per-category/ - DENSE_RANK window function."""
    limit = int(request.GET.get("limit", 3))
    result = get_top_products_by_category(limit)
    return success_response(result)


@api_view(["GET"])
@permission_classes([AllowAny])
def products_above_avg(request):
    """GET /api/v1/products/above-category-avg/ - correlated subquery."""
    category_id = request.GET.get("category_id")
    result = get_products_above_avg_price(category_id)
    return success_response(result)


@api_view(["GET"])
@permission_classes([AllowAny])
def never_purchased(request):
    """GET /api/v1/products/never-purchased/ - anti-join."""
    result = get_unsold_products()
    return success_response(result)


# ── Seller management ──────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_products(request):
    """GET /api/v1/products/seller/ - seller's own products."""
    page, page_size = validate_pagination_params(
        request.GET.get("page"), request.GET.get("page_size")
    )
    rows, total = get_seller_catalog(request.user.id, page, page_size)
    return paginated_response(rows, total, page, page_size)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_create(request):
    """POST /api/v1/products/seller/ - create a new product."""
    data = request.data
    if not data.get("name") or not data.get("category_id") or not data.get("base_price"):
        return error_response("name, category_id, and base_price are required",
                              "VALIDATION_ERROR", status=status.HTTP_400_BAD_REQUEST)
    try:
        product_id = seller_create_product(
            seller_id=request.user.id,
            name=data["name"],
            category_id=data["category_id"],
            base_price=data["base_price"],
            description=data.get("description", ""),
            slug=data.get("slug"),
        )
    except ValueError as e:
        return error_response(str(e), "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST)

    return success_response({"product_id": product_id, "message": "Product created"},
                           status=status.HTTP_201_CREATED)

2
@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_update(request, product_id):
    """PUT /api/v1/products/seller/{id}/ - update own product."""
    try:
        affected = seller_update_product(
            seller_id=request.user.id,
            product_id=product_id,
            name=request.data.get("name"),
            description=request.data.get("description"),
            base_price=request.data.get("base_price"),
            status=request.data.get("status"),
            category_id=request.data.get("category_id"),
        )
    except PermissionError:
        return error_response("You do not own this product", "PERMISSION_DENIED",
                              status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return error_response(str(e), "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)

    return success_response({"updated": affected})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_delete(request, product_id):
    """DELETE /api/v1/products/seller/{id}/delete/ — soft-delete own product."""
    owner_id = get_product_owner_id(product_id)
    if owner_id != request.user.id and request.user.role != "admin":
        return error_response("You do not own this product", "PERMISSION_DENIED",
                              status=status.HTTP_403_FORBIDDEN)
    try:
        seller_update_product(
            seller_id=owner_id,
            product_id=product_id,
            status="deleted",
        )
    except Exception as e:
        return error_response(str(e), "NOT_FOUND", status=status.HTTP_404_NOT_FOUND)
    return success_response({"product_id": product_id, "status": "deleted"})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_add_variant(request, product_id):
    """POST /api/v1/products/seller/{id}/variants/ - add a variant."""

    owner_id = get_product_owner_id(product_id)

    if owner_id is None:
        return error_response(
            "Product not found",
            "NOT_FOUND",
            status=status.HTTP_404_NOT_FOUND
        )

    if owner_id != request.user.id and request.user.role != "admin":
        return error_response(
            "You do not own this product",
            "PERMISSION_DENIED",
            status=status.HTTP_403_FORBIDDEN
        )

    data = request.data

    sku = data.get("sku")
    variant_name = data.get("variant_name")
    price = data.get("price")
    stock_quantity = data.get("stock_quantity", 0)
    attributes = data.get("attributes")

    if not sku or not variant_name or price is None:
        return error_response(
            "sku, variant_name, and price are required",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST
        )

    if not isinstance(attributes, (dict, type(None))):
        return error_response(
            "attributes must be a JSON object",
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        variant_id = create_product_variant(
            product_id=product_id,
            sku=sku,
            variant_name=variant_name,
            price=price,
            stock_quantity=stock_quantity,
            attributes=attributes,
        )

        return success_response(
            {"variant_id": variant_id},
            status=status.HTTP_201_CREATED
        )

    except ValueError as e:
        return error_response(
            str(e),
            "VALIDATION_ERROR",
            status=status.HTTP_400_BAD_REQUEST
        )
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def seller_add_image(request, product_id):
    """POST /api/v1/products/seller/{id}/images/ - add an image."""
    owner_id = get_product_owner_id(product_id)
    if owner_id != request.user.id and request.user.role != "admin":
        return error_response("You do not own this product", "PERMISSION_DENIED",
                              status=status.HTTP_403_FORBIDDEN)

    data = request.data
    if not data.get("image_url"):
        return error_response("image_url is required", "VALIDATION_ERROR",
                              status=status.HTTP_400_BAD_REQUEST)

    image_id = add_product_image(
        product_id=product_id,
        image_url=data["image_url"],
        alt_text=data.get("alt_text", ""),
        display_order=data.get("display_order", 0),
    )
    return success_response({"image_id": image_id}, status=status.HTTP_201_CREATED)
