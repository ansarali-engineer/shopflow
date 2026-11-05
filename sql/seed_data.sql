-- ShopFlow Seed Data
-- Execute: mysql -u shopflow_user -p shopflow < sql/seed_data.sql

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE coupon_redemptions;
TRUNCATE TABLE payments;
TRUNCATE TABLE shipments;
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
TRUNCATE TABLE inventory_movements;
TRUNCATE TABLE cart_items;
TRUNCATE TABLE carts;
TRUNCATE TABLE reviews;
TRUNCATE TABLE product_images;
TRUNCATE TABLE product_variants;
TRUNCATE TABLE products;
TRUNCATE TABLE categories;
TRUNCATE TABLE addresses;
TRUNCATE TABLE users;
TRUNCATE TABLE coupons;
TRUNCATE TABLE audit_logs;
SET FOREIGN_KEY_CHECKS = 1;

-- Sample account password: TestPass123!
-- Hash generated with Django's configured Argon2 hasher.
INSERT INTO users (email, password_hash, first_name, last_name, role, status) VALUES
('admin@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'Admin', 'User', 'admin', 'active'),
('seller1@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'John', 'Seller', 'seller', 'active'),
('seller2@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'Jane', 'Merchant', 'seller', 'active'),
('customer1@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'Alice', 'Buyer', 'customer', 'active'),
('customer2@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'Bob', 'Shopper', 'customer', 'active'),
('customer3@shopflow.test', 'argon2$argon2id$v=19$m=102400,t=2,p=8$VW5WNUtVUWJXTWt6TmtBYUFwbFp2bw$rtsT39EQ9lBubb4xpWAAZpllbOyWGInWYs60LHHWy0c', 'Charlie', 'Customer', 'customer', 'active');

-- Addresses
INSERT INTO addresses (user_id, label, street_line1, city, state, postal_code, country, is_default) VALUES
(4, 'Home', '123 Main St', 'Austin', 'TX', '78701', 'US', TRUE),
(4, 'Work', '456 Office Blvd', 'Austin', 'TX', '78702', 'US', FALSE),
(5, 'Home', '789 Oak Ave', 'Dallas', 'TX', '75201', 'US', TRUE),
(6, 'Home', '321 Pine St', 'Houston', 'TX', '77001', 'US', TRUE);

-- Categories (hierarchical)
INSERT INTO categories (name, slug, parent_id) VALUES
('Electronics', 'electronics', NULL),
('Computers', 'computers', 1),
('Laptops', 'laptops', 2),
('Desktops', 'desktops', 2),
('Phones', 'phones', 1),
('Smartphones', 'smartphones', 5),
('Accessories', 'accessories', 1),
('Audio', 'audio', 1),
('Headphones', 'headphones', 8),
('Speakers', 'speakers', 8),
('Clothing', 'clothing', NULL),
('Men', 'men', 11),
('Women', 'women', 11),
('Books', 'books', NULL),
('Fiction', 'fiction', 14),
('Non-Fiction', 'non-fiction', 14);

-- Products
INSERT INTO products (seller_id, category_id, name, slug, description, base_price, status) VALUES
(2, 3, 'ProBook 15', 'probook-15', '15-inch professional laptop', 1299.99, 'active'),
(2, 3, 'UltraBook Air', 'ultrabook-air', 'Ultra-thin laptop', 999.99, 'active'),
(2, 6, 'Galaxy Phone Pro', 'galaxy-phone-pro', 'Flagship smartphone', 799.99, 'active'),
(2, 7, 'USB-C Hub', 'usb-c-hub', 'Multi-port USB-C adapter', 49.99, 'active'),
(2, 9, 'Noise-Cancel Headphones', 'noise-cancel-headphones', 'Premium ANC headphones', 199.99, 'active'),
(3, 11, 'Cotton T-Shirt', 'cotton-tshirt', '100% cotton t-shirt', 24.99, 'active'),
(3, 12, 'Denim Jeans', 'denim-jeans', 'Classic denim jeans', 59.99, 'active'),
(3, 14, 'The Python Guide', 'python-guide', 'Complete Python programming guide', 39.99, 'active'),
(3, 15, 'Advanced SQL', 'advanced-sql', 'Master SQL and databases', 44.99, 'active'),
(2, 4, 'Gaming Desktop', 'gaming-desktop', 'High-performance gaming PC', 1899.99, 'active');

-- Product Variants
INSERT INTO product_variants (product_id, sku, variant_name, price, stock_quantity, reserved_quantity, status) VALUES
(1, 'PROBOOK-15-512', '512GB SSD / 16GB RAM', 1299.99, 25, 0, 'active'),
(1, 'PROBOOK-15-1TB', '1TB SSD / 32GB RAM', 1799.99, 10, 0, 'active'),
(2, 'UBAIR-256', '256GB / 8GB RAM', 999.99, 30, 0, 'active'),
(2, 'UBAIR-512', '512GB / 16GB RAM', 1199.99, 15, 0, 'active'),
(3, 'GALAXY-PRO-128', '128GB Black', 799.99, 100, 0, 'active'),
(3, 'GALAXY-PRO-256', '256GB Black', 899.99, 50, 0, 'active'),
(4, 'USBC-HUB-7', '7-in-1 Hub', 49.99, 200, 0, 'active'),
(5, 'ANC-HP-BLK', 'Black', 199.99, 40, 0, 'active'),
(5, 'ANC-HP-WHT', 'White', 199.99, 15, 0, 'active'),
(6, 'TSHIRT-M-BLK', 'Medium Black', 24.99, 500, 0, 'active'),
(6, 'TSHIRT-L-WHT', 'Large White', 24.99, 300, 0, 'active'),
(7, 'JEANS-32-BLU', '32 Blue', 59.99, 80, 0, 'active'),
(7, 'JEANS-34-BLK', '34 Black', 59.99, 60, 0, 'active'),
(8, 'BOOK-PY-001', 'Paperback', 39.99, 150, 0, 'active'),
(9, 'BOOK-SQL-001', 'Paperback', 44.99, 120, 0, 'active'),
(10, 'GAMING-PC-RTX', 'RTX 4080 / 32GB', 1899.99, 5, 0, 'active');

-- Product Images  (real Unsplash photos – no auth required)
INSERT INTO product_images (product_id, image_url, alt_text, display_order) VALUES
(1,  'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80', 'ProBook 15 laptop', 0),
(1,  'https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&q=80', 'ProBook 15 keyboard', 1),
(2,  'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=600&q=80', 'UltraBook Air side view', 0),
(3,  'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80', 'Galaxy Phone Pro', 0),
(3,  'https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=600&q=80', 'Galaxy Phone Pro back', 1),
(4,  'https://images.unsplash.com/photo-1625842268584-8f3296236761?w=600&q=80', 'USB-C Hub ports', 0),
(5,  'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80', 'Noise-Cancel Headphones', 0),
(5,  'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=600&q=80', 'Headphones side', 1),
(6,  'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80', 'Cotton T-Shirt', 0),
(7,  'https://images.unsplash.com/photo-1542272604-787c3835535d?w=600&q=80', 'Denim Jeans', 0),
(8,  'https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&q=80', 'The Python Guide book', 0),
(9,  'https://images.unsplash.com/photo-1589998059171-988d887df646?w=600&q=80', 'Advanced SQL book', 0),
(10, 'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&q=80', 'Gaming Desktop', 0),
(10, 'https://images.unsplash.com/photo-1593640408182-31c228c5e5da?w=600&q=80', 'Gaming Desktop internals', 1);

-- Coupons
INSERT INTO coupons (code, description, discount_type, discount_value, min_order_amount, max_discount_amount, per_customer_limit, status) VALUES
('WELCOME10', '10% off first order', 'percentage', 10.00, 0.00, 100.00, 1, 'active'),
('SAVE20', '$20 off orders over $100', 'fixed', 20.00, 100.00, 20.00, 5, 'active'),
('FREESHIP', 'Free shipping on any order', 'fixed', 9.99, 0.00, 9.99, 10, 'active');

-- Carts
INSERT INTO carts (user_id) VALUES (4), (5), (6);

-- Cart Items
INSERT INTO cart_items (cart_id, variant_id, quantity) VALUES
(1, 1, 1), (1, 7, 2),
(2, 6, 1),
(3, 14, 1);

-- Sample Orders
INSERT INTO orders (customer_id, order_number, status, subtotal, discount_amount, shipping_cost, tax_amount, total_amount, shipping_address_id) VALUES
(4, 'ORD-20250115-00001', 'DELIVERED', 1299.99, 0.00, 9.99, 104.00, 1413.98, 1),
(4, 'ORD-20250220-00002', 'DELIVERED', 49.99, 0.00, 9.99, 4.00, 63.98, 1),
(5, 'ORD-20250310-00003', 'DELIVERED', 799.99, 80.00, 9.99, 57.60, 787.58, 3),
(5, 'ORD-20250405-00004', 'SHIPPED', 199.99, 0.00, 9.99, 16.00, 225.98, 3),
(6, 'ORD-20250512-00005', 'DELIVERED', 59.99, 0.00, 9.99, 4.80, 74.78, 4),
(4, 'ORD-20250601-00006', 'PAID', 1199.99, 0.00, 9.99, 96.00, 1305.98, 1),
(6, 'ORD-20250715-00007', 'PENDING_PAYMENT', 39.99, 0.00, 9.99, 3.20, 53.18, 4),
(5, 'ORD-20250820-00008', 'DELIVERED', 1899.99, 0.00, 0.00, 152.00, 2051.99, 3);

-- Order Items
INSERT INTO order_items (order_id, product_id, variant_id, quantity, unit_price, line_total) VALUES
(1, 1, 1, 1, 1299.99, 1299.99),
(2, 4, 7, 1, 49.99, 49.99),
(3, 3, 6, 1, 799.99, 799.99),
(4, 5, 8, 1, 199.99, 199.99),
(5, 7, 12, 1, 59.99, 59.99),
(6, 2, 4, 1, 1199.99, 1199.99),
(7, 8, 14, 1, 39.99, 39.99),
(8, 10, 16, 1, 1899.99, 1899.99);

-- Payments
INSERT INTO payments (order_id, payment_method, amount, status, transaction_ref) VALUES
(1, 'card', 1413.98, 'success', 'MOCK-ABC1234567890'),
(2, 'card', 63.98, 'success', 'MOCK-DEF2345678901'),
(3, 'card', 787.58, 'success', 'MOCK-GHI3456789012'),
(4, 'card', 225.98, 'success', 'MOCK-JKL4567890123'),
(5, 'card', 74.78, 'success', 'MOCK-MNO5678901234'),
(6, 'card', 1305.98, 'success', 'MOCK-PQR6789012345'),
(7, 'card', 53.18, 'pending', NULL),
(8, 'card', 2051.99, 'success', 'MOCK-STU7890123456');

-- Inventory Movements
INSERT INTO inventory_movements (variant_id, movement_type, quantity, reason, order_id) VALUES
(1, 'stock_in', 100, 'Initial stock', NULL),
(1, 'sale', 1, 'Order ORD-20250115-00001', 1),
(7, 'stock_in', 300, 'Initial stock', NULL),
(7, 'sale', 1, 'Order ORD-20250220-00002', 2),
(6, 'stock_in', 200, 'Initial stock', NULL),
(6, 'sale', 1, 'Order ORD-20250310-00003', 3),
(8, 'stock_in', 60, 'Initial stock', NULL),
(8, 'sale', 1, 'Order ORD-20250405-00004', 4),
(12, 'stock_in', 100, 'Initial stock', NULL),
(12, 'sale', 1, 'Order ORD-20250512-00005', 5),
(4, 'stock_in', 50, 'Initial stock', NULL),
(4, 'sale', 1, 'Order ORD-20250601-00006', 6),
(14, 'stock_in', 200, 'Initial stock', NULL),
(14, 'reserve', 1, 'Order ORD-20250715-00007', 7),
(16, 'stock_in', 10, 'Initial stock', NULL),
(16, 'sale', 1, 'Order ORD-20250820-00008', 8);

-- Reviews
INSERT INTO reviews (product_id, user_id, rating, title, body) VALUES
(1, 4, 5, 'Excellent laptop', 'Fast, lightweight, great battery life.'),
(1, 5, 4, 'Good but pricey', 'Performance is great, but the price is high.'),
(3, 4, 5, 'Best phone I''ve owned', 'Amazing camera and battery.'),
(3, 6, 3, 'Decent but not perfect', 'Good phone but software needs updates.'),
(5, 5, 5, 'Noise cancellation is incredible', 'Blocks out everything.'),
(8, 6, 4, 'Solid guide', 'Covers the basics well.');

-- Audit Logs
INSERT INTO audit_logs (user_id, action, entity_type, entity_id, new_values) VALUES
(2, 'PRODUCT_CREATED', 'product', 1, '{"name":"ProBook 15"}'),
(4, 'ORDER_CREATED', 'order', 1, '{"order_number":"ORD-20250115-00001"}'),
(4, 'PAYMENT_SUCCESS', 'payment', 1, '{"transaction_ref":"MOCK-ABC1234567890"}');
