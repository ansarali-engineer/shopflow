-- ============================================================
-- ShopFlow Database Provisioning
-- Creates the databases and the application user referenced by .env.
-- Run ONCE as a MySQL admin (root), BEFORE loading schema.sql/seed_data.sql.
--
--   Get-Content sql\provision.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
--
-- Credentials here must match .env (DB_USER / DB_PASSWORD).
-- ============================================================

CREATE DATABASE IF NOT EXISTS shopflow
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS shopflow_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create the app user for both localhost (TCP/loopback) and remote-style hosts.
CREATE USER IF NOT EXISTS 'shopflow_user'@'localhost' IDENTIFIED BY 'StrongPass123!';
CREATE USER IF NOT EXISTS 'shopflow_user'@'%'        IDENTIFIED BY 'StrongPass123!';

-- (Re)set the password in case the account already existed with a different one.
ALTER USER 'shopflow_user'@'localhost' IDENTIFIED BY 'StrongPass123!';
ALTER USER 'shopflow_user'@'%'        IDENTIFIED BY 'StrongPass123!';

GRANT ALL PRIVILEGES ON shopflow.*      TO 'shopflow_user'@'localhost';
GRANT ALL PRIVILEGES ON shopflow.*      TO 'shopflow_user'@'%';
GRANT ALL PRIVILEGES ON shopflow_test.* TO 'shopflow_user'@'localhost';
GRANT ALL PRIVILEGES ON shopflow_test.* TO 'shopflow_user'@'%';

FLUSH PRIVILEGES;
