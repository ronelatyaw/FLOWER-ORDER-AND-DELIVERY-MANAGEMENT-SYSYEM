CREATE DATABASE IF NOT EXISTS flower_shop_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flower_shop_db;

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) DEFAULT NULL,
    email VARCHAR(120) DEFAULT NULL,
    address VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO admin_accounts (email, password_hash)
SELECT 'admin@margesflowershop.com',
       'scrypt:32768:8:1$0ZDL5sbBztDx2RhA$acef81b34fe0bd6919ccfc3e8b9da379092fb123c728fd2ab4a7312e6dec222897275168ed34dfdfd2a051c4644051905f973212472aa1c13c020ccc29f4dd8a'
WHERE NOT EXISTS (
    SELECT 1 FROM admin_accounts WHERE email='admin@margesflowershop.com'
);

CREATE TABLE IF NOT EXISTS customer_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_accounts_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_password_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_password_resets_account FOREIGN KEY (account_id)
        REFERENCES customer_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL DEFAULT 'Bouquet',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    stock INT NOT NULL DEFAULT 0,
    image VARCHAR(20) NOT NULL DEFAULT '🌷',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_code VARCHAR(20) UNIQUE DEFAULT NULL,
    customer_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status ENUM('Pending','Processing','On Delivery','Delivered','Cancelled') NOT NULL DEFAULT 'Pending',
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_orders_product FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO customers (name, phone, email, address)
SELECT 'Juan Dela Cruz','09171234567','juan@example.com','Iloilo City'
WHERE NOT EXISTS (SELECT 1 FROM customers WHERE email='juan@example.com');
INSERT INTO customers (name, phone, email, address)
SELECT 'Maria Santos','09181234567','maria@example.com','Pavia, Iloilo'
WHERE NOT EXISTS (SELECT 1 FROM customers WHERE email='maria@example.com');
INSERT INTO customers (name, phone, email, address)
SELECT 'Ana Reyes','09191234567','ana@example.com','Oton, Iloilo'
WHERE NOT EXISTS (SELECT 1 FROM customers WHERE email='ana@example.com');

INSERT INTO products (name, category, price, stock, image)
SELECT 'Red Rose Bouquet','Rose Bouquet',799.00,12,'🌹'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='Red Rose Bouquet');
INSERT INTO products (name, category, price, stock, image)
SELECT 'Sunflower Bouquet','Sunflower',899.00,8,'🌻'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='Sunflower Bouquet');
INSERT INTO products (name, category, price, stock, image)
SELECT 'Pink Rose Bouquet','Rose Bouquet',999.00,4,'🌸'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='Pink Rose Bouquet');
INSERT INTO products (name, category, price, stock, image)
SELECT 'Mixed Flower Bouquet','Mixed Flowers',799.00,3,'💐'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='Mixed Flower Bouquet');
INSERT INTO products (name, category, price, stock, image)
SELECT 'White Rose Bouquet','Rose Bouquet',899.00,2,'🤍'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='White Rose Bouquet');
INSERT INTO products (name, category, price, stock, image)
SELECT 'Tulip Bouquet','Tulips',799.00,5,'🌷'
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='Tulip Bouquet');

INSERT INTO orders (order_code, customer_id, product_id, quantity, total, status, order_date)
SELECT 'FOD-0001', c.id, p.id, 1, p.price, 'Delivered', DATE_SUB(NOW(), INTERVAL 1 DAY)
FROM customers c JOIN products p ON p.name='Red Rose Bouquet'
WHERE c.email='juan@example.com'
AND NOT EXISTS (SELECT 1 FROM orders WHERE order_code='FOD-0001');
INSERT INTO orders (order_code, customer_id, product_id, quantity, total, status, order_date)
SELECT 'FOD-0002', c.id, p.id, 1, p.price, 'On Delivery', DATE_SUB(NOW(), INTERVAL 2 DAY)
FROM customers c JOIN products p ON p.name='Sunflower Bouquet'
WHERE c.email='maria@example.com'
AND NOT EXISTS (SELECT 1 FROM orders WHERE order_code='FOD-0002');
INSERT INTO orders (order_code, customer_id, product_id, quantity, total, status, order_date)
SELECT 'FOD-0003', c.id, p.id, 2, p.price*2, 'Processing', DATE_SUB(NOW(), INTERVAL 3 DAY)
FROM customers c JOIN products p ON p.name='Pink Rose Bouquet'
WHERE c.email='ana@example.com'
AND NOT EXISTS (SELECT 1 FROM orders WHERE order_code='FOD-0003');
