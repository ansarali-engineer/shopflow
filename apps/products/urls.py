"""Product URL routes."""
from django.urls import path
from apps.products.views import (
    product_list, product_detail, category_tree, category_subtree,
    top_products_per_category, products_above_avg, never_purchased,
    seller_products, seller_create, seller_update,
    seller_add_variant, seller_add_image,
)

urlpatterns = [
    # Catalog (public)
    path("", product_list),
    path("<int:product_id>/", product_detail),
    # Categories (public)
    path("categories/", category_tree),
    path("categories/<str:slug>/", category_subtree),
    # Advanced SQL demos (public)
    path("top-per-category/", top_products_per_category),
    path("above-category-avg/", products_above_avg),
    path("never-purchased/", never_purchased),
    # Seller management (authenticated)
    path("seller/", seller_products),
    path("seller/create/", seller_create),
    path("seller/<int:product_id>/", seller_update),
    path("seller/<int:product_id>/variants/", seller_add_variant),
    path("seller/<int:product_id>/images/", seller_add_image),
]
