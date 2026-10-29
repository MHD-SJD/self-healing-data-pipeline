{{ config(materialized='table') }}

SELECT
    customer_id,
    email,
    first_name,
    last_name,
    signup_at,
    country,
    phone,
    _ingested_at AS updated_at
FROM {{ ref('stg_customers') }}

