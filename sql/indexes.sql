-- ShopFlow Supplemental Indexes
-- Execute AFTER schema.sql: mysql -u shopflow_user -p shopflow < sql\indexes.sql

-- Product catalog search performance
CREATE INDEX idx_products_cat_status ON products (category_id, status);
CREATE INDEX idx_variants_prod_price ON product_variants (product_id, price);
CREATE INDEX idx_variants_stock ON product_variants (stock_quantity, reserved_quantity);

-- Order lookup performance
CREATE INDEX idx_orders_customer_status ON orders (customer_id, status);
CREATE INDEX idx_orders_created_status ON orders (created_at, status);
CREATE INDEX idx_orderitems_product_order ON order_items (product_id, order_id);

-- Payment lookups
CREATE INDEX idx_payments_status_created ON payments (status, created_at);

-- Inventory movement queries
CREATE INDEX idx_movements_variant_type ON inventory_movements (variant_id, movement_type);

-- Review queries
CREATE INDEX idx_reviews_product_rating ON reviews (product_id, rating, status);

-- Coupon redemption lookups
CREATE INDEX idx_redemptions_coupon_user ON coupon_redemptions (coupon_id, user_id);

-- Audit log queries
CREATE INDEX idx_audit_action_created ON audit_logs (action, created_at);
CREATE INDEX idx_audit_entity_type_id ON audit_logs (entity_type, entity_id);
