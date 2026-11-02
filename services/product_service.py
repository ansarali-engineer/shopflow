"""Product service - catalog, search, seller management business logic."""
import logging
from decimal import Decimal

from repositories.product_repository import (
    get_product_detail, get_product_variants, get_product_images,
    get_products_list, get_category_tree, get_category_subtree,
    create_product, create_product_variant, add_product_image,
    get_seller_products, get_product_owner_id, update_product,
    get_top_products_per_category, get_products_above_category_avg_price,
    get_never_purchased_products, get_product_rating_summary,
)
from database.connection import RecordNotFoundError
from database.query_helpers import serialize_row, serialize_rows

logger = logging.getLogger("shopflow.services.product")


def get_catalog_product(product_id):
    """Get full product detail with variants, images, and rating summary."""
    product = get_product_detail(product_id)
    if not product:
        return None

    product["variants"] = get_product_variants(product_id)
    product["images"] = get_product_images(product_id)
    rating = get_product_rating_summary(product_id)
    if rating:
        product["rating_summary"] = serialize_row(rating)

    return serialize_row(product)


def search_products(**kwargs):
    """Search and filter the product catalog."""
    rows, total = get_products_list(**kwargs)
    return serialize_rows(rows), total


def get_categories():
    """Get the full hierarchical category tree."""
    tree = get_category_tree()
    return serialize_rows(tree)


def get_category_descendants(category_id):
    """Get a category and all its descendants."""
    tree = get_category_subtree(category_id)
    return serialize_rows(tree)


def seller_create_product(seller_id, name, category_id, base_price, description="", slug=None):
    """Create a new product owned by the seller."""
    # Validate price is positive
    price = Decimal(str(base_price))
    if price <= 0:
        raise ValueError("Price must be positive")

    product_id = create_product(
        seller_id=seller_id, name=name, category_id=category_id,
        base_price=str(price), description=description, slug=slug,
    )
    logger.info("Product created: id=%s, seller=%s", product_id, seller_id)
    return product_id


def seller_update_product(seller_id, product_id, **kwargs):
    """Update a product, verifying ownership first."""
    owner_id = get_product_owner_id(product_id)
    if owner_id != seller_id:
        raise PermissionError("You do not own this product")

    affected = update_product(product_id, **kwargs)
    if affected == 0:
        raise RecordNotFoundError("Product not found")
    return affected


def get_seller_catalog(seller_id, page=1, page_size=20):
    """Get paginated products for a seller."""
    rows, total = get_seller_products(seller_id, page, page_size)
    return serialize_rows(rows), total


def get_top_products_by_category(limit=3):
    """Get top N products by revenue in each category (window function)."""
    return serialize_rows(get_top_products_per_category(limit))


def get_products_above_avg_price(category_id=None):
    """Products priced above their category average (correlated subquery)."""
    return serialize_rows(get_products_above_category_avg_price(category_id))


def get_unsold_products():
    """Products never ordered (anti-join)."""
    return serialize_rows(get_never_purchased_products())
