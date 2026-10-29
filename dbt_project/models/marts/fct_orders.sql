{{ config(materialized='table') }}

SELECT
    o.order_id,
    o.customer_id,
    o.product_id,
    o.ordered_at,
    o.amount,
    o.status,
    o.shipping_address,
    o._batch_id,
    o._ingested_at
FROM {{ ref('stg_orders') }} o
INNER JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id

