-- Independent live review of the agreed cohort; never passed to the agent.
-- Bind period_start/period_end as inclusive/exclusive TIMESTAMP and parity as INT64.
WITH permitted_items AS (
  SELECT oi.id AS item_id, oi.order_id, oi.user_id,
    oi.product_id, u.state, p.category, p.department,
    DATE_TRUNC(DATE(oi.created_at, 'UTC'), MONTH) AS month,
    CAST(oi.sale_price AS NUMERIC) AS price
  FROM `bigquery-public-data.thelook_ecommerce.order_items` AS oi
  INNER JOIN `bigquery-public-data.thelook_ecommerce.orders` AS o
    ON oi.order_id = o.order_id AND oi.user_id = o.user_id
  INNER JOIN `bigquery-public-data.thelook_ecommerce.products` AS p ON oi.product_id = p.id
  INNER JOIN `bigquery-public-data.thelook_ecommerce.users` AS u ON oi.user_id = u.id
  WHERE MOD(p.id, 2) = @parity
    AND oi.created_at >= @period_start AND oi.created_at < @period_end
    AND oi.status = 'Complete' AND o.status = 'Complete' AND oi.returned_at IS NULL
), aggregates AS (
  SELECT 'total' AS grain, '' AS label, SUM(price) AS revenue,
    COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT user_id) AS buyers,
    COUNT(DISTINCT item_id) AS items, COUNT(*) AS fact_rows
  FROM permitted_items HAVING COUNT(DISTINCT user_id) >= 5
  UNION ALL
  SELECT 'state', state, SUM(price), COUNT(DISTINCT order_id), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id), COUNT(*)
  FROM permitted_items GROUP BY state HAVING COUNT(DISTINCT user_id) >= 5
  UNION ALL
  SELECT 'month', CAST(month AS STRING), SUM(price), COUNT(DISTINCT order_id), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id), COUNT(*)
  FROM permitted_items GROUP BY month HAVING COUNT(DISTINCT user_id) >= 5
  UNION ALL
  SELECT 'category', category, SUM(price), COUNT(DISTINCT order_id), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id), COUNT(*)
  FROM permitted_items GROUP BY category HAVING COUNT(DISTINCT user_id) >= 5
  UNION ALL
  SELECT 'department', department, SUM(price), COUNT(DISTINCT order_id), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id), COUNT(*)
  FROM permitted_items GROUP BY department HAVING COUNT(DISTINCT user_id) >= 5
  UNION ALL
  SELECT 'product_id', CAST(product_id AS STRING), SUM(price), COUNT(DISTINCT order_id), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id), COUNT(*)
  FROM permitted_items GROUP BY product_id HAVING COUNT(DISTINCT user_id) >= 5
)
SELECT * FROM aggregates ORDER BY grain, label
