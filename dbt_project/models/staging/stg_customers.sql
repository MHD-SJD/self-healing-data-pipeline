{{ config(materialized='view') }}

WITH source_data AS (
    SELECT
        customer_id,
        LOWER(TRIM(email)) AS email,
        TRIM(first_name) AS first_name,
        TRIM(last_name) AS last_name,
        signup_date::timestamp AS signup_at,
        UPPER(TRIM(country)) AS country,
        phone,
        _batch_id,
        _ingested_at
    FROM {{ source('raw_data', 'raw_customers') }}
    WHERE customer_id IS NOT NULL 
      AND customer_id != ''
      AND customer_id NOT IN (
          SELECT source_identifier 
          FROM pipeline_metadata.quarantined_records 
          WHERE dataset_name = 'customers' AND source_identifier IS NOT NULL
      )
),
deduplicated AS (
    SELECT DISTINCT ON (customer_id)
        customer_id,
        email,
        first_name,
        last_name,
        signup_at,
        country,
        phone,
        _batch_id,
        _ingested_at
    FROM source_data
    ORDER BY customer_id, signup_at DESC NULLS LAST
)

SELECT * FROM deduplicated

