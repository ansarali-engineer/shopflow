"""Order, checkout, and inventory tests."""
import pytest
from decimal import Decimal
from repositories.cart_repository import get_or_create_cart, add_cart_item, get_cart_items
from repositories.order_repository import get_order_status
from repositories.inventory_repository import get_variant_stock
from services.order_service import checkout, transition_order_status


class TestCheckout:
    def test_successful_checkout(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        addr_id = db_cursor.lastrowid
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 2)
        order = checkout(test_user["id"], addr_id)
        assert order["order_number"].startswith("ORD-")
        assert order["status"] == "PENDING_PAYMENT"
        assert Decimal(order["total_amount"]) > 0
        assert len(order["items"]) == 1

    def test_empty_cart_fails(self, db_cursor, test_user):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        with pytest.raises(ValueError, match="empty"):
            checkout(test_user["id"], db_cursor.lastrowid)

    def test_insufficient_stock_fails(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 100)
        with pytest.raises(ValueError, match="Insufficient stock"):
            checkout(test_user["id"], db_cursor.lastrowid)

    def test_stock_reserved(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 5)
        checkout(test_user["id"], db_cursor.lastrowid)
        stock = get_variant_stock(sample_product["variant_id"])
        assert stock["reserved_quantity"] == 5; assert stock["available_stock"] == 45

    def test_cart_cleared(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        checkout(test_user["id"], db_cursor.lastrowid)
        assert get_cart_items(cart_id) == []

    def test_price_captured_at_purchase(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        db_cursor.execute("UPDATE product_variants SET price = %s WHERE id = %s", ["999.99", sample_product["variant_id"]])
        db_cursor.execute("SELECT unit_price FROM order_items WHERE order_id = %s", [order["id"]])
        assert str(db_cursor.fetchone()[0]) == "299.99"


class TestOrderStatus:
    def test_valid_transition(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        transition_order_status(order["id"], "PAID", test_user["id"])
        assert get_order_status(order["id"]) == "PAID"

    def test_invalid_transition(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        with pytest.raises(ValueError, match="Invalid transition"):
            transition_order_status(order["id"], "SHIPPED", test_user["id"])

    def test_full_lifecycle(self, db_cursor, test_user, sample_product):
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        for s in ["PAID", "PROCESSING", "SHIPPED", "DELIVERED"]:
            transition_order_status(order["id"], s, test_user["id"])
        assert get_order_status(order["id"]) == "DELIVERED"


class TestPaymentIdempotency:
    def test_duplicate_processing_idempotent(self, db_cursor, test_user, sample_product):
        from services.payment_service import process_mock_payment
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        pid = order["payments"][0]["id"]
        r1 = process_mock_payment(pid, success=True); assert r1["status"] == "success"
        r2 = process_mock_payment(pid, success=True); assert r2["status"] == "success"

    def test_failed_payment_keeps_order_pending(self, db_cursor, test_user, sample_product):
        from services.payment_service import process_mock_payment
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid)
        result = process_mock_payment(order["payments"][0]["id"], success=False)
        assert result["status"] == "failed"
        assert get_order_status(order["id"]) == "PENDING_PAYMENT"


class TestCouponCheckout:
    def test_coupon_reduces_total(self, db_cursor, test_user, sample_product):
        from repositories.coupon_repository import create_coupon
        db_cursor.execute("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                          [test_user["id"], "Home", "123 St", "Austin"])
        create_coupon("TEST10", "percentage", "10")
        cart_id = get_or_create_cart(test_user["id"])
        add_cart_item(cart_id, sample_product["variant_id"], 1)
        order = checkout(test_user["id"], db_cursor.lastrowid, coupon_code="TEST10")
        assert Decimal(order["discount_amount"]) > 0
        assert Decimal(order["discount_amount"]) == (Decimal(order["subtotal"]) * Decimal("0.10")).quantize(Decimal("0.01"))
