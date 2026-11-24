-- ============================================================================
-- SILVER LAYER - Clean, normalize, de-duplicate, prepare for embedding
-- ----------------------------------------------------------------------------
-- Materialized views (batch reads over bronze) that standardize descriptors and
-- merchant attributes while PRESERVING the original raw descriptor for
-- traceability. silver_merchants also builds the embedding_text used by Vector
-- Search (merchant name + aliases + location + category).
-- ============================================================================

CREATE OR REFRESH MATERIALIZED VIEW silver_transactions
  COMMENT 'Cleaned transactions: whitespace-normalized descriptor plus a display normalization. Raw descriptor preserved for traceability.'
AS SELECT
    transaction_id,
    CAST(transaction_date AS TIMESTAMP)                                   AS transaction_ts,
    to_date(CAST(transaction_date AS TIMESTAMP))                          AS transaction_date,
    date_trunc('MONTH', CAST(transaction_date AS TIMESTAMP))              AS transaction_month,
    transaction_amount,
    currency,
    country,
    -- raw facilitator hint from the feed (may be UNKNOWN); real extraction is done by the LLM
    payment_facilitator                                                   AS raw_facilitator_hint,
    raw_transaction_descriptor,
    -- normalized, human-readable descriptor (collapse whitespace, upper-case)
    upper(trim(regexp_replace(raw_transaction_descriptor, '\\s+', ' ')))  AS normalized_descriptor
FROM bronze_transactions;


CREATE OR REFRESH MATERIALIZED VIEW silver_merchant_aliases
  COMMENT 'De-duplicated, trimmed merchant aliases. One row per (merchant_id, normalized alias).'
AS SELECT merchant_id, alias_name, alias_type
FROM (
    SELECT
        merchant_id,
        trim(alias_name)                               AS alias_name,
        alias_type,
        row_number() OVER (
            PARTITION BY merchant_id, lower(trim(alias_name))
            ORDER BY alias_type
        ) AS rn
    FROM bronze_merchant_aliases
    WHERE alias_name IS NOT NULL AND length(trim(alias_name)) > 0
)
WHERE rn = 1;


CREATE OR REFRESH MATERIALIZED VIEW silver_merchants
  COMMENT 'De-duplicated canonical merchants with normalized location fields and a prepared embedding_text (name + aliases + location + category) for Vector Search.'
AS
WITH deduped AS (
    SELECT * EXCEPT(rn) FROM (
        SELECT
            *,
            row_number() OVER (PARTITION BY merchant_id ORDER BY _ingested_at DESC) AS rn
        FROM bronze_merchants
    ) WHERE rn = 1
),
alias_agg AS (
    SELECT merchant_id, array_join(collect_set(alias_name), ' | ') AS alias_blob,
           count(*) AS alias_count
    FROM silver_merchant_aliases
    GROUP BY merchant_id
)
SELECT
    d.merchant_id,
    trim(d.merchant_name)                      AS merchant_name,
    trim(d.address)                            AS address,
    initcap(trim(d.city))                      AS city,
    upper(trim(d.state))                       AS state,
    upper(trim(d.country))                     AS country,
    trim(d.postal_code)                        AS postal_code,
    d.merchant_category,
    d.website,
    d.phone_number,
    coalesce(a.alias_count, 0)                 AS alias_count,
    -- embedding input: canonical name, known aliases, location, category
    concat_ws(' | ',
        trim(d.merchant_name),
        coalesce(a.alias_blob, ''),
        concat_ws(' ', initcap(trim(d.city)), upper(trim(d.state)), trim(d.postal_code)),
        d.merchant_category
    )                                          AS embedding_text
FROM deduped d
LEFT JOIN alias_agg a USING (merchant_id);
