"""pytest fixtures for ShopFlow integration tests."""
import pytest
from django.db import connection
from repositories.user_repository import create_user
from services.auth_service import _generate_tokens


@pytest.fixture
def db_cursor():
    cursor = connection.cursor()
    yield cursor
    cursor.close()


@pytest.fixture(autouse=True)
def reset_test_data(db_cursor):
    tables = [
        "coupon_redemptions", "payments", "shipments", "order_items",
        "orders", "inventory_movements", "cart_items", "carts",
        "reviews", "product_images", "product_variants", "products",
        "addresses", "users", "categories", "coupons", "audit_logs",
    ]
    db_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in tables:
        db_cursor.execute(f"TRUNCATE TABLE {table}")
    db_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    yield


@pytest.fixture
def test_user(db_cursor):
    return create_user("testuser@shopflow.test", "TestPass123!", "Test", "User", "customer")

@pytest.fixture
def test_seller(db_cursor):
    return create_user("testseller@shopflow.test", "TestPass123!", "Test", "Seller", "seller")

@pytest.fixture
def test_admin(db_cursor):
    return create_user("testadmin@shopflow.test", "TestPass123!", "Test", "Admin", "admin")

@pytest.fixture
def user_token(test_user):
    return _generate_tokens(test_user["id"], "customer")["access_token"]

@pytest.fixture
def seller_token(test_seller):
    return _generate_tokens(test_seller["id"], "seller")["access_token"]

@pytest.fixture
def admin_token(test_admin):
    return _generate_tokens(test_admin["id"], "admin")["access_token"]

@pytest.fixture
def auth_client(user_token):
    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    return client

@pytest.fixture
def seller_client(seller_token):
    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {seller_token}")
    return client

@pytest.fixture
def admin_client(admin_token):
    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
    return client

@pytest.fixture
def sample_category(db_cursor):
    db_cursor.execute("INSERT INTO categories (name, slug) VALUES (%s, %s)", ["Electronics", "electronics"])
    return db_cursor.lastrowid

@pytest.fixture
def sample_product(db_cursor, test_seller, sample_category):
    db_cursor.execute(
        "INSERT INTO products (seller_id, category_id, name, slug, description, base_price, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        [test_seller["id"], sample_category, "Test Phone", "test-phone", "A test phone", "299.99", "active"],
    )
    product_id = db_cursor.lastrowid
    db_cursor.execute(
        "INSERT INTO product_variants (product_id, sku, variant_name, price, stock_quantity, reserved_quantity, status) "
        "VALUES (%s, %s, %s, %s, %s, 0, %s)",
        [product_id, "TEST-001", "Standard", "299.99", 50, "active"],
    )
    return {"product_id": product_id, "variant_id": db_cursor.lastrowid}
