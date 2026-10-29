{{ config(materialized='view') }}

WITH source_data AS (
    SELECT
        product_id,
        sku,
        product_name,
        category,
        unit_price::numeric(10, 2) AS unit_price,
        stock_quantity::integer AS stock_quantity,
        warehouse_code,
        last_restocked_at::timestamp AS last_restocked_at,
        _batch_id,
        _ingested_at
    FROM {{ source('raw_data', 'raw_inventory') }}
    WHERE product_id IS NOT NULL 
      AND product_id != ''
      AND product_id NOT IN (
          SELECT source_identifier 
          FROM pipeline_metadata.quarantined_records 
          WHERE dataset_name = 'inventory' AND source_identifier IS NOT NULL
      )
),
deduplicated AS (
    SELECT DISTINCT ON (product_id)
        product_id,
        sku,
        product_name,
        category,
        unit_price,
        stock_quantity,
        warehouse_code,
        last_restocked_at,
        _batch_id,
        _ingested_at
    FROM source_data
    ORDER BY product_id, last_restocked_at DESC NULLS LAST
)

SELECT * FROM deduplicated

