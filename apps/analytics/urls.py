"""Analytics URL routes."""
from django.urls import path
from apps.analytics.views import (
    revenue_by_seller, monthly_sales_by_category, top_products,
    frequent_customers, categories_above_avg, no_order_customers,
    top_product_per_seller, above_avg_spenders, below_avg_stock,
    multi_category_orders, monthly_revenue, customer_ltv,
    product_ranking, category_revenue_rollup, sales_window,
    second_highest_per_category, customer_ranking, declining_months,
    order_status_summary, orders_export, inventory_alerts,
)

urlpatterns = [
    path("reports/revenue-by-seller/", revenue_by_seller),
    path("reports/monthly-sales-by-category/", monthly_sales_by_category),
    path("reports/top-products/", top_products),
    path("reports/frequent-customers/", frequent_customers),
    path("reports/categories-above-avg/", categories_above_avg),
    path("reports/no-order-customers/", no_order_customers),
    path("reports/top-product-per-seller/", top_product_per_seller),
    path("reports/above-avg-spenders/", above_avg_spenders),
    path("reports/below-avg-stock/", below_avg_stock),
    path("reports/multi-category-orders/", multi_category_orders),
    path("reports/monthly-revenue/", monthly_revenue),
    path("customers/lifetime-value/", customer_ltv),
    path("reports/product-ranking/", product_ranking),
    path("reports/category-revenue-rollup/", category_revenue_rollup),
    path("reports/sales-window/", sales_window),
    path("reports/second-highest-per-category/", second_highest_per_category),
    path("customers/ranked-by-spending/", customer_ranking),
    path("reports/declining-months/", declining_months),
    path("reports/order-status-summary/", order_status_summary),
    path("orders/export/", orders_export),
    path("reports/inventory-alerts/", inventory_alerts),
]
