-- ============================================================================
-- GOLD LAYER - Curated business entities
-- ----------------------------------------------------------------------------
-- Curated, analytics-ready transaction and canonical merchant tables. These are
-- the business entities consumed by the enrichment workflow (Vector Search reads
-- gold_merchants) and by analytics.
--
-- NOTE: The three enrichment ANALYTICS gold tables required for Genie
--   (gold_enrichment_results, gold_merchant_metrics, gold_enrichment_quality_metrics)
-- are populated downstream by lakebase/sync_to_uc.py and evaluation/, because
-- they depend on enrichment outcomes that do not exist at pipeline time.
-- ============================================================================

CREATE OR REFRESH MATERIALIZED VIEW gold_transactions
  (
    transaction_id             COMMENT 'Unique transaction identifier (primary key).',
    transaction_ts             COMMENT 'Transaction timestamp.',
    transaction_date           COMMENT 'Transaction calendar date.',
    transaction_month          COMMENT 'Month bucket (first day of month) for time-series analytics.',
    transaction_amount         COMMENT 'Transaction amount in the transaction currency.',
    currency                   COMMENT 'ISO currency code.',
    country                    COMMENT 'Country where the transaction occurred.',
    raw_facilitator_hint       COMMENT 'Payment-facilitator hint from the raw feed (may be UNKNOWN); authoritative facilitator is produced by LLM extraction.',
    raw_transaction_descriptor COMMENT 'Original unstructured merchant descriptor as received from the payment network.',
    normalized_descriptor      COMMENT 'Whitespace-normalized, upper-cased descriptor for display.'
  )
  COMMENT 'Curated card transactions ready for enrichment and analytics (one row per transaction).'
AS SELECT
    transaction_id,
    transaction_ts,
    transaction_date,
    transaction_month,
    transaction_amount,
    currency,
    country,
    raw_facilitator_hint,
    raw_transaction_descriptor,
    normalized_descriptor
FROM silver_transactions;


CREATE OR REFRESH MATERIALIZED VIEW gold_merchants
  (
    merchant_id       COMMENT 'Canonical unique merchant identifier (primary key).',
    merchant_name     COMMENT 'Canonical merchant display name.',
    address           COMMENT 'Street address of the merchant location.',
    city              COMMENT 'Merchant city (title-cased).',
    state             COMMENT 'Merchant state (upper-cased 2-letter code).',
    country           COMMENT 'Merchant country.',
    postal_code       COMMENT 'Merchant postal / ZIP code.',
    merchant_category COMMENT 'Merchant business category (e.g. Coffee Shop, Grocery, Gas Station).',
    website           COMMENT 'Merchant website URL.',
    phone_number      COMMENT 'Merchant contact phone number.',
    alias_count       COMMENT 'Number of known alternative names (aliases) for this merchant.',
    embedding_text    COMMENT 'Concatenated text (name + aliases + location + category) used to generate the Vector Search embedding.'
  )
  COMMENT 'Canonical merchant master: the governed source of merchant identities used as Vector Search candidates and for analytics joins.'
AS SELECT
    merchant_id,
    merchant_name,
    address,
    city,
    state,
    country,
    postal_code,
    merchant_category,
    website,
    phone_number,
    alias_count,
    embedding_text
FROM silver_merchants;


-- Pipeline-level business metric: raw transaction volume by month and facilitator hint.
-- (Enrichment-outcome metrics live in gold_merchant_metrics / gold_enrichment_quality_metrics,
--  produced after enrichment by the sync + evaluation steps.)
CREATE OR REFRESH MATERIALIZED VIEW gold_transaction_volume_metrics
  COMMENT 'Raw ingestion business metric: transaction counts and amounts by month and raw facilitator hint.'
AS SELECT
    transaction_month,
    raw_facilitator_hint,
    count(*)                                   AS transaction_count,
    round(sum(transaction_amount), 2)          AS total_amount,
    round(avg(transaction_amount), 2)          AS avg_amount
FROM gold_transactions
GROUP BY transaction_month, raw_facilitator_hint;
