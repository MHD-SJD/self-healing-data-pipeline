{{ config(materialized='table') }}

SELECT
    product_id,
    sku,
    product_name,
    category,
    unit_price,
    warehouse_code,
    last_restocked_at,
    _ingested_at AS updated_at
FROM {{ ref('stg_inventory') }}

