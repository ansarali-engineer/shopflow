"""
Product repository - product catalog, search, and seller management SQL.

SQL patterns:
  1. Multi-table JOIN with derived subqueries (avoids row multiplication)
  2. Dynamic WHERE clause from a conditions list
  3. FULLTEXT search
  4. Safe ORDER BY via allowlist mapping
  5. Recursive CTE for category tree
  6. Window functions (DENSE_RANK) for top-N-per-group
  7. Correlated subquery for above-average pricing
  8. Anti-join (LEFT JOIN + IS NULL) for never-purchased products
"""
import logging
from datetime import datetime

from database.query_helpers import (
    fetch_one, fetch_all, fetch_scalar, insert_one, update_or_delete,
    fetch_paginated, safe_sort_fragment,
)

logger = logging.getLogger("shopflow.repositories.product")

SORT_ALLOWLIST = {
    "newest": "p.created_at DESC", "oldest": "p.created_at ASC",
    "price_asc": "min_price ASC", "price_desc": "min_price DESC",
    "name_asc": "p.name ASC", "name_desc": "p.name DESC",
    "rating_desc": "avg_rating DESC", "popularity": "review_count DESC",
}


def get_product_detail(product_id):
    sql = """SELECT p.id, p.seller_id, p.name, p.slug, p.description, p.base_price, p.status, p.created_at, p.updated_at,
             c.id AS category_id, c.name AS category_name, c.slug AS category_slug,
             u.first_name AS seller_first_name, u.last_name AS seller_last_name,
             (SELECT MIN(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS min_price,
             (SELECT MAX(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS max_price,
             (SELECT SUM(pv.stock_quantity - pv.reserved_quantity) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS total_available_stock,
             (SELECT COALESCE(AVG(r.rating), 0) FROM reviews r WHERE r.product_id = p.id AND r.status = 'published') AS avg_rating,
             (SELECT COUNT(*) FROM reviews r WHERE r.product_id = p.id AND r.status = 'published') AS review_count,
             (SELECT COUNT(*) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS variant_count,
             (SELECT pi.image_url FROM product_images pi
              WHERE pi.product_id = p.id
              ORDER BY pi.display_order ASC, pi.id ASC LIMIT 1) AS image_url
             FROM products p
             INNER JOIN categories c ON p.category_id = c.id
             INNER JOIN users u ON p.seller_id = u.id
             WHERE p.id = %s"""
    return fetch_one(sql, [product_id])


def get_product_variants(product_id):
    sql = """SELECT pv.id, pv.product_id, pv.sku, pv.variant_name, pv.attributes, pv.price,
             pv.stock_quantity, pv.reserved_quantity, (pv.stock_quantity - pv.reserved_quantity) AS available_stock, pv.status
             FROM product_variants pv WHERE pv.product_id = %s ORDER BY pv.price ASC"""
    return fetch_all(sql, [product_id])


def get_product_images(product_id):
    sql = """SELECT id, product_id, image_url, alt_text, display_order
             FROM product_images WHERE product_id = %s ORDER BY display_order ASC, id ASC"""
    return fetch_all(sql, [product_id])


def get_products_list(search=None, category_id=None, min_price=None, max_price=None,
                      seller_id=None, min_rating=None, in_stock=None, sort=None, page=1, page_size=20):
    conditions = ["p.status = %s"]
    params = ["active"]

    if search:
        conditions.append("MATCH(p.name, p.description) AGAINST(%s IN NATURAL LANGUAGE MODE)")
        params.append(search)
    if category_id is not None:
        conditions.append("p.category_id IN (WITH RECURSIVE cat_tree AS (SELECT id FROM categories WHERE id = %s UNION ALL SELECT c.id FROM categories c INNER JOIN cat_tree ct ON c.parent_id = ct.id) SELECT id FROM cat_tree)")
        params.append(category_id)
    if min_price is not None:
        conditions.append("(SELECT MIN(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') >= %s")
        params.append(min_price)
    if max_price is not None:
        conditions.append("(SELECT MIN(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') <= %s")
        params.append(max_price)
    if seller_id is not None:
        conditions.append("p.seller_id = %s"); params.append(seller_id)
    if min_rating is not None:
        conditions.append("(SELECT COALESCE(AVG(r.rating), 0) FROM reviews r WHERE r.product_id = p.id AND r.status = 'published') >= %s")
        params.append(min_rating)
    if in_stock:
        conditions.append("(SELECT SUM(pv.stock_quantity - pv.reserved_quantity) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') > 0")

    where_clause = " AND ".join(conditions)
    order_by = safe_sort_fragment(sort, SORT_ALLOWLIST, default="newest")

    sql = f"""SELECT p.id, p.name, p.slug, p.description, p.base_price, p.status, p.created_at,
             c.id AS category_id, c.name AS category_name,
             u.first_name AS seller_first_name, u.last_name AS seller_last_name,
             (SELECT MIN(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS min_price,
             (SELECT MAX(pv.price) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS max_price,
             (SELECT SUM(pv.stock_quantity - pv.reserved_quantity) FROM product_variants pv WHERE pv.product_id = p.id AND pv.status = 'active') AS available_stock,
             (SELECT COALESCE(AVG(r.rating), 0) FROM reviews r WHERE r.product_id = p.id AND r.status = 'published') AS avg_rating,
             (SELECT COUNT(*) FROM reviews r WHERE r.product_id = p.id AND r.status = 'published') AS review_count,
             (SELECT pi.image_url FROM product_images pi
              WHERE pi.product_id = p.id
              ORDER BY pi.display_order ASC, pi.id ASC LIMIT 1) AS image_url
             FROM products p
             INNER JOIN categories c ON p.category_id = c.id
             INNER JOIN users u ON p.seller_id = u.id
             WHERE {where_clause}
             ORDER BY {order_by}"""
    return fetch_paginated(sql, params, page, page_size)


def get_category_tree():
    sql = """WITH RECURSIVE category_tree AS (
             SELECT id, name, slug, parent_id, 0 AS depth, CAST(CONCAT(LPAD(id, 8, '0')) AS CHAR(255)) AS path
             FROM categories WHERE parent_id IS NULL
             UNION ALL
             SELECT c.id, c.name, c.slug, c.parent_id, ct.depth + 1, CAST(CONCAT(ct.path, '-', LPAD(c.id, 8, '0')) AS CHAR(255))
             FROM categories c INNER JOIN category_tree ct ON c.parent_id = ct.id
             ) SELECT id, name, slug, parent_id, depth, path FROM category_tree ORDER BY path"""
    return fetch_all(sql)


def get_category_subtree(category_id):
    sql = """WITH RECURSIVE category_tree AS (
             SELECT id, name, slug, parent_id, 0 AS depth FROM categories WHERE id = %s
             UNION ALL
             SELECT c.id, c.name, c.slug, c.parent_id, ct.depth + 1 FROM categories c INNER JOIN category_tree ct ON c.parent_id = ct.id
             ) SELECT id, name, slug, parent_id, depth FROM category_tree ORDER BY depth, name"""
    return fetch_all(sql, [category_id])


def create_product(seller_id, name, category_id, base_price, description="", slug=None, status="active"):
    if not slug: slug = name.lower().replace(" ", "-").replace("--", "-")[:100]
    sql = """INSERT INTO products (seller_id, category_id, name, slug, description, base_price, status)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    return insert_one(sql, [seller_id, category_id, name, slug, description, base_price, status])


import json

def create_product_variant(
    product_id,
    sku,
    variant_name,
    price,
    stock_quantity=0,
    attributes=None,
    status="active"
):
    attributes_json = (
        json.dumps(attributes)
        if attributes is not None
        else None
    )

    sql = """
        INSERT INTO product_variants
        (
            product_id,
            sku,
            variant_name,
            attributes,
            price,
            stock_quantity,
            reserved_quantity,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
    """

    return insert_one(sql, [
        product_id,
        sku,
        variant_name,
        attributes_json,
        price,
        stock_quantity,
        status
    ])


def add_product_image(product_id, image_url, alt_text="", display_order=0):
    sql = """INSERT INTO product_images (product_id, image_url, alt_text, display_order)
             VALUES (%s, %s, %s, %s)"""
    return insert_one(sql, [product_id, image_url, alt_text, display_order])


def get_seller_products(seller_id, page=1, page_size=20):
    sql = """SELECT p.id, p.name, p.slug, p.description, p.base_price, p.status, p.created_at,
             c.name AS category_name,
             (SELECT COUNT(*) FROM product_variants pv WHERE pv.product_id = p.id) AS variant_count,
             (SELECT COALESCE(SUM(pv.stock_quantity), 0) FROM product_variants pv WHERE pv.product_id = p.id) AS total_stock
             FROM products p INNER JOIN categories c ON p.category_id = c.id
             WHERE p.seller_id = %s ORDER BY p.created_at DESC"""
    return fetch_paginated(sql, [seller_id], page, page_size)


def get_product_owner_id(product_id):
    return fetch_scalar("SELECT seller_id FROM products WHERE id = %s", [product_id])


def update_product(product_id, name=None, description=None, base_price=None, status=None, category_id=None):
    sets, params = [], []
    if name is not None: sets.append("name = %s"); params.append(name)
    if description is not None: sets.append("description = %s"); params.append(description)
    if base_price is not None: sets.append("base_price = %s"); params.append(base_price)
    if status is not None: sets.append("status = %s"); params.append(status)
    if category_id is not None: sets.append("category_id = %s"); params.append(category_id)
    if not sets: return 0
    sets.append("updated_at = %s"); params.append(datetime.utcnow()); params.append(product_id)
    sql = f"UPDATE products SET {', '.join(sets)} WHERE id = %s"
    return update_or_delete(sql, params)


def get_top_products_per_category(limit=3):
    """
    Returns top N products per category ranked by revenue (DENSE_RANK window fn).
    Includes all fields required by the ProductCard component:
      id, name, category_id, category_name, min_price, max_price, base_price,
      available_stock, image_url, avg_rating, review_count,
      seller_first_name, seller_last_name, revenue, rank_in_category.
    """
    sql = """
        SELECT *
        FROM (
            SELECT
                p.id,
                p.name,
                p.base_price,
                p.slug,
                p.status,
                c.id   AS category_id,
                c.name AS category_name,
                u.first_name AS seller_first_name,
                u.last_name  AS seller_last_name,
                -- Price range from active variants (fall back to base_price)
                COALESCE(
                    (SELECT MIN(pv.price) FROM product_variants pv
                     WHERE pv.product_id = p.id AND pv.status = 'active'),
                    p.base_price
                ) AS min_price,
                COALESCE(
                    (SELECT MAX(pv.price) FROM product_variants pv
                     WHERE pv.product_id = p.id AND pv.status = 'active'),
                    p.base_price
                ) AS max_price,
                -- Available stock across all active variants
                COALESCE(
                    (SELECT SUM(pv.stock_quantity - pv.reserved_quantity)
                     FROM product_variants pv
                     WHERE pv.product_id = p.id AND pv.status = 'active'),
                    0
                ) AS available_stock,
                -- Primary image (lowest display_order)
                (SELECT pi.image_url FROM product_images pi
                 WHERE pi.product_id = p.id
                 ORDER BY pi.display_order ASC, pi.id ASC
                 LIMIT 1) AS image_url,
                -- Rating summary
                COALESCE(
                    (SELECT AVG(r.rating) FROM reviews r
                     WHERE r.product_id = p.id AND r.status = 'published'),
                    0
                ) AS avg_rating,
                (SELECT COUNT(*) FROM reviews r
                 WHERE r.product_id = p.id AND r.status = 'published') AS review_count,
                -- Revenue and ranking
                COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue,
                DENSE_RANK() OVER (
                    PARTITION BY c.id
                    ORDER BY COALESCE(SUM(oi.quantity * oi.unit_price), 0) DESC
                ) AS rank_in_category
            FROM products p
            INNER JOIN categories c ON p.category_id = c.id
            INNER JOIN users      u ON p.seller_id   = u.id
            LEFT JOIN order_items oi ON oi.product_id = p.id
            LEFT JOIN orders o
                   ON o.id = oi.order_id
                  AND o.status NOT IN ('CANCELLED', 'REFUNDED')
            WHERE p.status = 'active'
            GROUP BY
                p.id, p.name, p.base_price, p.slug, p.status,
                c.id, c.name,
                u.first_name, u.last_name
        ) ranked
        WHERE rank_in_category <= %s
        ORDER BY category_name ASC, rank_in_category ASC
    """
    return fetch_all(sql, [limit])


def get_products_above_category_avg_price(category_id=None):
    where = ""
    params = []
    if category_id is not None:
        where = "AND p.category_id = %s"; params.append(category_id)
    sql = f"""SELECT p.id, p.name, p.base_price, c.name AS category_name,
             (SELECT AVG(p2.base_price) FROM products p2 WHERE p2.category_id = p.category_id AND p2.status = 'active') AS category_avg_price
             FROM products p INNER JOIN categories c ON p.category_id = c.id
             WHERE p.base_price > (SELECT AVG(p3.base_price) FROM products p3 WHERE p3.category_id = p.category_id AND p3.status = 'active')
             AND p.status = 'active' {where} ORDER BY p.base_price DESC"""
    return fetch_all(sql, params)


def get_never_purchased_products():
    sql = """SELECT p.id, p.name, p.base_price, c.name AS category_name, p.created_at
             FROM products p LEFT JOIN order_items oi ON oi.product_id = p.id
             LEFT JOIN categories c ON p.category_id = c.id
             WHERE oi.id IS NULL AND p.status = 'active' ORDER BY p.created_at DESC"""
    return fetch_all(sql)


def get_product_rating_summary(product_id):
    sql = """SELECT COUNT(*) AS total_reviews, COALESCE(AVG(rating), 0) AS avg_rating,
             SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) AS five_star,
             SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) AS four_star,
             SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS three_star,
             SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) AS two_star,
             SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS one_star
             FROM reviews WHERE product_id = %s AND status = 'published'"""
    return fetch_one(sql, [product_id])
