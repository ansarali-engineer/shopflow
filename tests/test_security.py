"""Security, permissions, and financial accuracy tests."""
import pytest
from decimal import Decimal
from django.db import IntegrityError
from apps.authentication.backends import ShopFlowUser
from repositories.user_repository import create_user
from database.connection import DuplicateRecordError


def test_shopflow_user_pk_alias_matches_id():
    user = ShopFlowUser(id=42, email="user@example.com", role="customer")
    assert user.pk == user.id


class TestAuthRequired:
    def test_no_profile_without_auth(self, client):
        assert client.get("/api/v1/users/me/").status_code == 401
    def test_no_cart_without_auth(self, client):
        assert client.get("/api/v1/cart/").status_code == 401
    def test_no_checkout_without_auth(self, client):
        assert client.post("/api/v1/orders/checkout/", {}, format="json").status_code == 401


class TestRolePermissions:
    def test_customer_no_seller_access(self, auth_client):
        assert auth_client.get("/api/v1/products/seller/").status_code == 403
    def test_customer_no_admin_reports(self, auth_client):
        assert auth_client.get("/api/v1/analytics/reports/revenue-by-seller/").status_code == 403
    def test_seller_no_admin_reports(self, seller_client):
        assert seller_client.get("/api/v1/analytics/reports/revenue-by-seller/").status_code == 403
    def test_admin_can_access(self, admin_client):
        assert admin_client.get("/api/v1/analytics/reports/revenue-by-seller/").status_code == 200


class TestSQLInjection:
    def test_login_injection(self, client):
        assert client.post("/api/v1/auth/login/", {"email":"' OR '1'='1","password":"x"}, format="json").status_code == 401
    def test_search_injection(self, client):
        assert client.get("/api/v1/products/?search=' OR 1=1; DROP TABLE users; --").status_code == 200
    def test_sort_injection(self, client):
        assert client.get("/api/v1/products/?sort=price; DROP TABLE products; --").status_code == 200
    def test_union_injection(self, db_cursor, test_user):
        from database.query_helpers import fetch_one
        assert fetch_one("SELECT id, email FROM users WHERE id = %s", ["0 UNION SELECT 1, 'hacked@evil.com'"]) is None


class TestFinancialAccuracy:
    def test_decimal_precision(self, db_cursor, test_user, sample_product):
        from repositories.cart_repository import get_or_create_cart, add_cart_item
        from services.order_service import checkout
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 3)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        assert Decimal(order["subtotal"]) == Decimal("899.97")
        subtotal = Decimal(order["subtotal"])
        expected = subtotal + Decimal("9.99") + (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))
        assert Decimal(order["total_amount"]) == expected

    def test_client_cannot_override_prices(self, db_cursor, test_user, sample_product):
        from repositories.cart_repository import get_or_create_cart, add_cart_item
        from services.order_service import checkout
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        db_cursor.execute("SELECT unit_price FROM order_items WHERE order_id = %s", [order["id"]])
        assert Decimal(str(db_cursor.fetchone()[0])) == Decimal("299.99")


class TestInputValidation:
    def test_duplicate_email(self, db_cursor, test_user):
        with pytest.raises((DuplicateRecordError, IntegrityError, ValueError)):
            create_user("testuser@shopflow.test", "TestPass123!", "Dup", "User", "customer")
    def test_negative_qty(self):
        from utils.validators import validate_quantity
        with pytest.raises(ValueError): validate_quantity(-1)
    def test_zero_qty(self):
        from utils.validators import validate_quantity
        with pytest.raises(ValueError): validate_quantity(0)
    def test_short_password(self):
        from utils.validators import validate_password
        with pytest.raises(ValueError): validate_password("short")
    def test_invalid_email(self):
        from utils.validators import validate_email
        with pytest.raises(ValueError): validate_email("notanemail")
    def test_invalid_transition(self):
        from utils.validators import validate_order_status_transition
        assert not validate_order_status_transition("DELIVERED", "PENDING_PAYMENT")
    def test_valid_transition(self):
        from utils.validators import validate_order_status_transition
        assert validate_order_status_transition("PENDING_PAYMENT", "PAID")


class TestDBConstraints:
    def test_unique_sku(self, db_cursor, sample_product):
        with pytest.raises(IntegrityError):
            db_cursor.execute("INSERT INTO product_variants (product_id, sku, variant_name, price, stock_quantity, status) "
                              "VALUES (%s, %s, %s, %s, %s, %s)",
                              [sample_product["product_id"], "TEST-001", "Dup", "10.00", 5, "active"])
    def test_fk_constraint(self, db_cursor):
        with pytest.raises(IntegrityError):
            db_cursor.execute("INSERT INTO orders (customer_id, order_number, status, subtotal, "
                              "discount_amount, shipping_cost, tax_amount, total_amount) "
                              "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                              [99999, "ORD-INVALID", "PENDING_PAYMENT", "0", "0", "0", "0", "0"])
