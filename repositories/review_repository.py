"""Review repository - product rating and feedback SQL."""
import logging
from database.query_helpers import fetch_one, fetch_all, fetch_scalar, insert_one, update_or_delete, fetch_paginated

logger = logging.getLogger("shopflow.repositories.review")


def create_review(product_id, user_id, rating, title, body=""):
    sql = "INSERT INTO reviews (product_id, user_id, rating, title, body, status) VALUES (%s, %s, %s, %s, %s, 'published')"
    return insert_one(sql, [product_id, user_id, rating, title, body])


def get_product_reviews(product_id, rating=None, page=1, page_size=10):
    conditions = ["r.product_id = %s", "r.status = 'published'"]
    params = [product_id]
    if rating is not None: conditions.append("r.rating = %s"); params.append(rating)
    where_clause = " AND ".join(conditions)
    sql = f"""SELECT r.id, r.product_id, r.user_id, r.rating, r.title, r.body, r.status, r.created_at,
             u.first_name AS reviewer_first_name, u.last_name AS reviewer_last_name
             FROM reviews r INNER JOIN users u ON r.user_id = u.id WHERE {where_clause} ORDER BY r.created_at DESC"""
    return fetch_paginated(sql, params, page, page_size)


def get_review_by_id(review_id):
    sql = """SELECT r.id, r.product_id, r.user_id, r.rating, r.title, r.body, r.status, r.created_at,
             u.first_name AS reviewer_first_name, u.last_name AS reviewer_last_name
             FROM reviews r INNER JOIN users u ON r.user_id = u.id WHERE r.id = %s"""
    return fetch_one(sql, [review_id])


def has_user_reviewed_product(product_id, user_id):
    count = fetch_scalar("SELECT COUNT(*) FROM reviews WHERE product_id = %s AND user_id = %s", [product_id, user_id]) or 0
    return count > 0


def update_review_status(review_id, status):
    return update_or_delete("UPDATE reviews SET status = %s WHERE id = %s", [status, review_id])
