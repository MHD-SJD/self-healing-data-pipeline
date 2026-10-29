{{ config(materialized='table') }}

SELECT
    product_id,
    sku,
    product_name,
    category,
    unit_price,
    stock_quantity,
    (unit_price * stock_quantity)::numeric(14, 2) AS total_inventory_value,
    warehouse_code,
    last_restocked_at,
    CASE 
        WHEN stock_quantity < 20 THEN 'CRITICAL_LOW'
        WHEN stock_quantity < 50 THEN 'LOW'
        ELSE 'OPTIMAL'
    END AS stock_status
FROM {{ ref('stg_inventory') }}

