"""Product catalog and search tests."""
import pytest
from database.query_helpers import fetch_one, fetch_scalar
from repositories.product_repository import (
    get_product_detail, get_products_list, get_category_tree,
    get_top_products_per_category, get_products_above_category_avg_price,
    get_never_purchased_products, get_product_owner_id, get_product_variants,
)


class TestProductDetail:
    def test_returns_product_with_category(self, db_cursor, sample_product):
        product = get_product_detail(sample_product["product_id"])
        assert product is not None; assert product["name"] == "Test Phone"
        assert product["category_name"] == "Electronics"

    def test_returns_none_for_missing(self): assert get_product_detail(99999) is None


class TestProductSearch:
    def test_search_by_name(self, db_cursor, sample_product):
        rows, total = get_products_list(search="phone")
        assert total >= 1; assert any(r["name"] == "Test Phone" for r in rows)

    def test_returns_empty_for_no_matches(self):
        rows, total = get_products_list(search="nonexistent_xyz")
        assert total == 0; assert rows == []


class TestCategoryTree:
    def test_returns_hierarchical(self, db_cursor):
        db_cursor.execute("INSERT INTO categories (name, slug) VALUES (%s, %s)", ["Parent", "parent"])
        parent_id = db_cursor.lastrowid
        db_cursor.execute("INSERT INTO categories (name, slug, parent_id) VALUES (%s, %s, %s)",
                         ["Child", "child", parent_id])
        tree = get_category_tree()
        parent = [c for c in tree if c["name"] == "Parent"][0]
        child = [c for c in tree if c["name"] == "Child"][0]
        assert parent["depth"] == 0; assert child["depth"] == 1


class TestTopProductsPerCategory:
    def test_returns_ranked(self, db_cursor, sample_product, test_user, sample_category):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "City"])
        addr_id = db_cursor.lastrowid
        db_cursor.execute(
            "INSERT INTO orders (customer_id, order_number, status, subtotal, discount_amount, "
            "shipping_cost, tax_amount, total_amount, shipping_address_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [test_user["id"], "ORD-TEST-001", "DELIVERED", "299.99", "0", "0", "0", "299.99", addr_id])
        order_id = db_cursor.lastrowid
        db_cursor.execute("INSERT INTO order_items (order_id, product_id, variant_id, quantity, unit_price, line_total) "
                          "VALUES (%s, %s, %s, %s, %s, %s)",
                          [order_id, sample_product["product_id"], sample_product["variant_id"], 1, "299.99", "299.99"])
        result = get_top_products_per_category(limit=3)
        assert len(result) >= 1; assert result[0]["rank_in_category"] == 1


class TestProductsAboveAveragePrice:
    def test_returns_above_avg(self, db_cursor, sample_category, test_seller):
        db_cursor.execute("INSERT INTO products (seller_id, category_id, name, slug, base_price, status) "
                          "VALUES (%s, %s, %s, %s, %s, %s)", [test_seller["id"], sample_category, "Cheap", "cheap", "10.00", "active"])
        db_cursor.execute("INSERT INTO products (seller_id, category_id, name, slug, base_price, status) "
                          "VALUES (%s, %s, %s, %s, %s, %s)", [test_seller["id"], sample_category, "Expensive", "expensive", "100.00", "active"])
        result = get_products_above_category_avg_price(category_id=sample_category)
        names = [r["name"] for r in result]
        assert "Expensive" in names; assert "Cheap" not in names


class TestNeverPurchased:
    def test_returns_unsold(self, db_cursor, sample_product):
        result = get_never_purchased_products()
        assert sample_product["product_id"] in [r["id"] for r in result]


class TestSQLInjectionPrevention:
    def test_injection_in_string_param(self, db_cursor, test_user):
        assert fetch_one("SELECT id, email FROM users WHERE email = %s", ["' OR '1'='1"]) is None

    def test_injection_in_int_param(self):
        assert fetch_scalar("SELECT COUNT(*) FROM users WHERE id = %s", ["1; DROP TABLE users; --"]) == 0

    def test_sort_param_cannot_inject(self):
        from database.query_helpers import safe_sort_fragment
        allowlist = {"newest": "created_at DESC", "name_asc": "name ASC"}
        result = safe_sort_fragment("name ASC; DROP TABLE users; --", allowlist)
        assert "DROP" not in result.upper()
