{{ config(materialized='view') }}

WITH source_data AS (
    SELECT
        order_id,
        customer_id,
        product_id,
        order_date::timestamp AS ordered_at,
        amount::numeric(12, 2) AS amount,
        UPPER(TRIM(status)) AS status,
        shipping_address,
        _batch_id,
        _ingested_at
    FROM {{ source('raw_data', 'raw_orders') }}
    WHERE order_id IS NOT NULL 
      AND order_id != ''
      AND amount IS NOT NULL
      AND amount::numeric > 0
      AND order_id NOT IN (
          SELECT source_identifier 
          FROM pipeline_metadata.quarantined_records 
          WHERE dataset_name = 'orders' AND source_identifier IS NOT NULL
      )
),
deduplicated AS (
    SELECT DISTINCT ON (order_id)
        order_id,
        customer_id,
        product_id,
        ordered_at,
        amount,
        status,
        shipping_address,
        _batch_id,
        _ingested_at
    FROM source_data
    ORDER BY order_id, ordered_at DESC NULLS LAST
)

SELECT * FROM deduplicated

