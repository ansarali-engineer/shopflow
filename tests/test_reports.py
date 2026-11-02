"""Report and analytics query tests."""
import pytest
from decimal import Decimal
from repositories.report_repository import (
    get_revenue_by_seller, get_best_selling_products,
    get_customers_with_more_than_n_orders, get_monthly_revenue_report,
    get_customer_lifetime_value, get_order_status_summary,
    get_orders_keyset_paginated, get_inventory_alerts,
)
from repositories.cart_repository import get_or_create_cart, add_cart_item
from services.order_service import checkout, transition_order_status


def _create_order(db_cursor, test_user, sample_product, qty=1, status="DELIVERED"):
    db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                      [test_user["id"], "Home", "123 St", "Austin"])
    cart_id = get_or_create_cart(test_user["id"])
    add_cart_item(cart_id, sample_product["variant_id"], qty)
    order = checkout(test_user["id"], db_cursor.lastrowid)
    if status != "PENDING_PAYMENT":
        for s in [("PAID","PAID"),("PROCESSING","PROCESSING"),("SHIPPED","SHIPPED"),("DELIVERED","DELIVERED")]:
            if status == s[0]:
                transition_order_status(order["id"], s[0], test_user["id"])
                break
            transition_order_status(order["id"], s[0], test_user["id"])
    return order


class TestRevenueBySeller:
    def test_returns_seller(self, db_cursor, test_user, test_seller, sample_product):
        _create_order(db_cursor, test_user, sample_product)
        result = get_revenue_by_seller()
        seller = [r for r in result if r["seller_email"] == "testseller@shopflow.test"]
        assert len(seller) == 1; assert Decimal(seller[0]["total_revenue"]) > 0


class TestBestSelling:
    def test_returns_ranked(self, db_cursor, test_user, sample_product):
        _create_order(db_cursor, test_user, sample_product, qty=3)
        result = get_best_selling_products(limit=10)
        assert len(result) >= 1; assert result[0]["total_quantity_sold"] >= 3


class TestFrequentCustomers:
    def test_multiple_orders(self, db_cursor, test_user, sample_product):
        for _ in range(3): _create_order(db_cursor, test_user, sample_product)
        result = get_customers_with_more_than_n_orders(min_orders=2)
        assert "testuser@shopflow.test" in [r["customer_email"] for r in result]


class TestMonthlyRevenue:
    def test_returns_monthly(self, db_cursor, test_user, sample_product):
        _create_order(db_cursor, test_user, sample_product)
        result = get_monthly_revenue_report()
        assert len(result) >= 1


class TestCustomerLTV:
    def test_returns_tier(self, db_cursor, test_user, sample_product):
        _create_order(db_cursor, test_user, sample_product)
        result = get_customer_lifetime_value()
        cust = [r for r in result if r["email"] == "testuser@shopflow.test"]
        assert len(cust) == 1; assert cust[0]["spending_tier"] in ("VIP","High Value","Regular","New")


class TestOrderStatusSummary:
    def test_returns_counts(self, db_cursor, test_user, sample_product):
        _create_order(db_cursor, test_user, sample_product)
        result = get_order_status_summary()
        assert result["total_orders"] >= 1; assert result["delivered"] >= 1


class TestKeysetPagination:
    def test_returns_rows(self, db_cursor, test_user, sample_product):
        _create_order(db_cursor, test_user, sample_product)
        rows, next_cursor = get_orders_keyset_paginated(0, 10)
        assert len(rows) >= 1


class TestInventoryAlerts:
    def test_low_stock(self, db_cursor, sample_product):
        db_cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE id = %s", [5, sample_product["variant_id"]])
        result = get_inventory_alerts(threshold=10)
        assert sample_product["variant_id"] in [r["variant_id"] for r in result]

    def test_out_of_stock(self, db_cursor, sample_product):
        db_cursor.execute("UPDATE product_variants SET stock_quantity = 0, reserved_quantity = 0 WHERE id = %s",
                          [sample_product["variant_id"]])
        result = get_inventory_alerts(threshold=10)
        m = [r for r in result if r["variant_id"] == sample_product["variant_id"]]
        if m: assert m[0]["stock_status"] == "OUT_OF_STOCK"
