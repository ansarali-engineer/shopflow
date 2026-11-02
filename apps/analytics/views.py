"""Analytics and reporting API views."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from utils.responses import success_response, error_response, paginated_response
from repositories.report_repository import (
    get_revenue_by_seller, get_monthly_sales_by_category,
    get_best_selling_products, get_customers_with_more_than_n_orders,
    get_categories_above_average_revenue, get_customers_with_no_completed_orders,
    get_highest_revenue_product_per_seller, get_customers_above_average_spending,
    get_products_with_below_average_category_stock, get_orders_with_multiple_categories,
    get_monthly_revenue_report, get_customer_lifetime_value,
    get_product_sales_ranking, get_category_revenue_rollup,
    get_sales_window_analysis, get_second_highest_revenue_per_category,
    get_customers_ranked_by_spending, get_consecutive_declining_months,
    get_order_status_summary, get_orders_keyset_paginated, get_inventory_alerts,
)
from permissions.role_permissions import IsAdmin, IsSellerOrAdmin
from database.query_helpers import serialize_row, serialize_rows


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def revenue_by_seller(request): return success_response(serialize_rows(get_revenue_by_seller()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def monthly_sales_by_category(request): return success_response(serialize_rows(get_monthly_sales_by_category()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def top_products(request): return success_response(serialize_rows(get_best_selling_products(int(request.GET.get("limit",10)))))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def frequent_customers(request): return success_response(serialize_rows(get_customers_with_more_than_n_orders(int(request.GET.get("min_orders",5)))))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def categories_above_avg(request): return success_response(serialize_rows(get_categories_above_average_revenue()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def no_order_customers(request): return success_response(serialize_rows(get_customers_with_no_completed_orders()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def top_product_per_seller(request): return success_response(serialize_rows(get_highest_revenue_product_per_seller()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def above_avg_spenders(request): return success_response(serialize_rows(get_customers_above_average_spending()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def below_avg_stock(request): return success_response(serialize_rows(get_products_with_below_average_category_stock()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def multi_category_orders(request): return success_response(serialize_rows(get_orders_with_multiple_categories()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def monthly_revenue(request): return success_response(serialize_rows(get_monthly_revenue_report()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def customer_ltv(request): return success_response(serialize_rows(get_customer_lifetime_value()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def product_ranking(request): return success_response(serialize_rows(get_product_sales_ranking()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def category_revenue_rollup(request): return success_response(serialize_rows(get_category_revenue_rollup()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def sales_window(request): return success_response(serialize_rows(get_sales_window_analysis()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def second_highest_per_category(request): return success_response(serialize_rows(get_second_highest_revenue_per_category()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def customer_ranking(request): return success_response(serialize_rows(get_customers_ranked_by_spending()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def declining_months(request): return success_response(serialize_rows(get_consecutive_declining_months()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def order_status_summary(request): return success_response(serialize_row(get_order_status_summary()))

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def orders_export(request):
    last_id = int(request.GET.get("last_id", 0)); limit = int(request.GET.get("page_size", 20))
    rows, next_cursor = get_orders_keyset_paginated(last_id, limit)
    return success_response({"rows": serialize_rows(rows), "next_cursor": next_cursor})

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSellerOrAdmin])
def inventory_alerts(request): return success_response(serialize_rows(get_inventory_alerts(int(request.GET.get("threshold",10)))))
