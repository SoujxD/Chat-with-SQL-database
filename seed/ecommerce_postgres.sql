-- Ecommerce analytics sample database.
-- Runs automatically on first Postgres container start (mounted into
-- /docker-entrypoint-initdb.d/ by docker-compose.yml).
--
-- Schema: categories -> products -> order_items <- orders -> customers.
-- Designed so common business questions have obvious answers, e.g.:
--   "What are the top 5 products by revenue?"
--   "Which customers have spent the most?"
--   "What's monthly revenue for the last year?"
--   "Which category has the best profit margin?"

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    name VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    cost NUMERIC(10, 2) NOT NULL
);

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    city VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL,
    signup_date DATE NOT NULL
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed'
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- ---- Categories ----
INSERT INTO categories (name) VALUES
    ('Electronics'), ('Home & Kitchen'), ('Sports & Outdoors'),
    ('Books'), ('Beauty'), ('Toys'), ('Clothing'), ('Grocery');

-- ---- Products (price/cost chosen for a believable ~40-60% margin) ----
INSERT INTO products (category_id, name, price, cost) VALUES
    (1, 'Wireless Earbuds', 59.99, 28.00),
    (1, '4K Streaming Stick', 39.99, 18.00),
    (1, 'Bluetooth Speaker', 44.99, 21.00),
    (1, 'Smartwatch', 129.99, 62.00),
    (2, 'Stand Mixer', 189.99, 95.00),
    (2, 'Non-Stick Pan Set', 64.99, 30.00),
    (2, 'Espresso Machine', 149.99, 70.00),
    (2, 'Air Fryer', 89.99, 42.00),
    (3, 'Yoga Mat', 24.99, 9.00),
    (3, 'Camping Tent (4-person)', 119.99, 55.00),
    (3, 'Trail Running Shoes', 79.99, 35.00),
    (3, 'Insulated Water Bottle', 19.99, 7.00),
    (4, 'The Pragmatic Data Analyst', 22.99, 8.00),
    (4, 'SQL for Everyone', 18.99, 6.50),
    (4, 'Atomic Habits', 16.99, 6.00),
    (5, 'Vitamin C Serum', 27.99, 9.50),
    (5, 'Hair Dryer', 34.99, 14.00),
    (5, 'Electric Toothbrush', 49.99, 20.00),
    (6, 'Building Block Set', 34.99, 14.00),
    (6, 'Remote Control Car', 44.99, 19.00),
    (7, 'Men''s Running Jacket', 69.99, 30.00),
    (7, 'Women''s Yoga Pants', 39.99, 16.00),
    (7, 'Cotton T-Shirt (3-pack)', 24.99, 9.00),
    (8, 'Organic Coffee Beans (1lb)', 14.99, 6.00),
    (8, 'Extra Virgin Olive Oil', 12.99, 5.00);

-- ---- Customers ----
INSERT INTO customers (name, email, city, country, signup_date) VALUES
    ('Ava Johnson', 'ava.johnson@example.com', 'New York', 'USA', '2024-01-12'),
    ('Liam Smith', 'liam.smith@example.com', 'Los Angeles', 'USA', '2024-02-03'),
    ('Olivia Brown', 'olivia.brown@example.com', 'Chicago', 'USA', '2024-01-25'),
    ('Noah Davis', 'noah.davis@example.com', 'Toronto', 'Canada', '2024-03-10'),
    ('Emma Wilson', 'emma.wilson@example.com', 'Vancouver', 'Canada', '2024-02-18'),
    ('Oliver Miller', 'oliver.miller@example.com', 'London', 'UK', '2024-01-05'),
    ('Sophia Moore', 'sophia.moore@example.com', 'Manchester', 'UK', '2024-04-02'),
    ('Elijah Taylor', 'elijah.taylor@example.com', 'Sydney', 'Australia', '2024-03-22'),
    ('Charlotte Anderson', 'charlotte.anderson@example.com', 'Melbourne', 'Australia', '2024-02-28'),
    ('James Thomas', 'james.thomas@example.com', 'Austin', 'USA', '2024-05-14'),
    ('Amelia Jackson', 'amelia.jackson@example.com', 'Seattle', 'USA', '2024-01-30'),
    ('Benjamin White', 'benjamin.white@example.com', 'Boston', 'USA', '2024-04-19'),
    ('Mia Harris', 'mia.harris@example.com', 'Dublin', 'Ireland', '2024-03-01'),
    ('Lucas Martin', 'lucas.martin@example.com', 'Berlin', 'Germany', '2024-02-11'),
    ('Isabella Thompson', 'isabella.thompson@example.com', 'Munich', 'Germany', '2024-05-06'),
    ('Henry Garcia', 'henry.garcia@example.com', 'Madrid', 'Spain', '2024-01-18'),
    ('Evelyn Martinez', 'evelyn.martinez@example.com', 'Barcelona', 'Spain', '2024-04-27'),
    ('Alexander Robinson', 'alexander.robinson@example.com', 'Paris', 'France', '2024-03-15'),
    ('Harper Clark', 'harper.clark@example.com', 'Lyon', 'France', '2024-02-08'),
    ('Daniel Lewis', 'daniel.lewis@example.com', 'Denver', 'USA', '2024-05-20');

-- ---- Orders + order items ----
-- Deterministic pseudo-random generation (fixed seed) spread over the last
-- 12 months so date-bucketed questions (monthly revenue, recent orders,
-- customer trends) have realistic-looking answers.
SELECT setseed(0.4213);

INSERT INTO orders (customer_id, order_date, status)
SELECT
    (floor(random() * 20) + 1)::int AS customer_id,
    (DATE '2025-07-04' - (floor(random() * 365))::int) AS order_date,
    (ARRAY['completed', 'completed', 'completed', 'completed', 'cancelled'])[floor(random() * 5)::int + 1] AS status
FROM generate_series(1, 180);

-- NOTE: picking the product via `JOIN LATERAL (... ORDER BY random() LIMIT 1)`
-- looks correlated per row, but Postgres's planner is free to evaluate an
-- uncorrelated LATERAL subquery once and reuse it — which is exactly what
-- happens here, so a naive version of this insert assigns every row the same
-- product. Assigning product_id via a row-varying arithmetic expression
-- sidesteps the issue entirely and still spreads rows across all products
-- (25 and 7 are coprime, so `row_number() * 7 mod 25` cycles through every
-- product before repeating).
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    x.order_id,
    (((row_number() OVER (ORDER BY x.order_id, x.item_no) * 7) + x.order_id) % 25) + 1 AS product_id,
    (floor(random() * 3) + 1)::int AS quantity,
    0 AS unit_price
FROM (
    SELECT order_id, generate_series(1, (floor(random() * 3) + 1)::int) AS item_no
    FROM orders
) x;

UPDATE order_items oi
SET unit_price = p.price
FROM products p
WHERE p.product_id = oi.product_id;
