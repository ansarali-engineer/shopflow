"""Coupon repository - discount code SQL operations."""
import logging
from datetime import datetime
from database.query_helpers import fetch_one, fetch_scalar, insert_one, update_or_delete, fetch_all

logger = logging.getLogger("shopflow.repositories.coupon")


def get_coupon_by_code(code):
    sql = """SELECT id, code, description, discount_type, discount_value, min_order_amount, max_discount_amount,
             valid_from, valid_until, max_redemptions, per_customer_limit, category_id, product_id, seller_id, status, created_at
             FROM coupons WHERE code = %s AND status = 'active'"""
    return fetch_one(sql, [code])


def get_coupon_redemption_count(coupon_id):
    return fetch_scalar("SELECT COUNT(*) FROM coupon_redemptions WHERE coupon_id = %s", [coupon_id]) or 0


def get_customer_coupon_redemption_count(coupon_id, user_id):
    return fetch_scalar("SELECT COUNT(*) FROM coupon_redemptions WHERE coupon_id = %s AND user_id = %s", [coupon_id, user_id]) or 0


def redeem_coupon(coupon_id, user_id, order_id, discount_amount):
    sql = "INSERT INTO coupon_redemptions (coupon_id, user_id, order_id, discount_amount) VALUES (%s, %s, %s, %s)"
    return insert_one(sql, [coupon_id, user_id, order_id, discount_amount])


def create_coupon(code, discount_type, discount_value, min_order_amount="0", max_discount_amount=None,
                   valid_from=None, valid_until=None, max_redemptions=None, per_customer_limit=1,
                   category_id=None, product_id=None, seller_id=None):
    sql = """INSERT INTO coupons (code, discount_type, discount_value, min_order_amount, max_discount_amount,
             valid_from, valid_until, max_redemptions, per_customer_limit, category_id, product_id, seller_id, status)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')"""
    return insert_one(sql, [code, discount_type, discount_value, min_order_amount, max_discount_amount,
                            valid_from, valid_until, max_redemptions, per_customer_limit,
                            category_id, product_id, seller_id])


def list_active_coupons():
    sql = """SELECT id, code, description, discount_type, discount_value, min_order_amount, max_discount_amount,
             valid_from, valid_until, max_redemptions, per_customer_limit, category_id, product_id, seller_id, status
             FROM coupons WHERE status = 'active' ORDER BY created_at DESC"""
    return fetch_all(sql)
