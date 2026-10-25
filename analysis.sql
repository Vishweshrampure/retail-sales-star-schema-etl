-- Example business questions answered from the star schema

-- 1. Monthly revenue
SELECT d.year, d.month, d.month_name, SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- 2. Revenue by product category
SELECT p.category, SUM(f.total_amount) AS revenue, SUM(f.quantity) AS units_sold
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY revenue DESC;

-- 3. Top 5 customers by revenue
SELECT c.customer_name, c.city, SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_name, c.city
ORDER BY revenue DESC
LIMIT 5;            -- SQL Server: use SELECT TOP 5 ... instead of LIMIT 5

-- 4. Revenue by city and category
SELECT c.city, p.category, SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY c.city, p.category
ORDER BY c.city, revenue DESC;
