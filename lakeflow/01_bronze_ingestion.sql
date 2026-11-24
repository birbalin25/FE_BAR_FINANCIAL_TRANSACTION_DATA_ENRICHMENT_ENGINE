-- ============================================================================
-- BRONZE LAYER - Raw ingestion via Auto Loader (Lakeflow Spark Declarative Pipeline)
-- ----------------------------------------------------------------------------
-- Ingests the synthetic source files from the Unity Catalog landing volume as
-- append-only streaming tables. Raw descriptors are preserved verbatim.
-- Data-quality expectations drop structurally invalid rows but keep messy
-- (but valid) descriptors - messiness is the business problem we solve later.
-- ============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_transactions
  (
    CONSTRAINT valid_txn_id   EXPECT (transaction_id IS NOT NULL) ON VIOLATION DROP ROW,
    CONSTRAINT valid_amount   EXPECT (transaction_amount >= 0),
    CONSTRAINT has_descriptor EXPECT (raw_transaction_descriptor IS NOT NULL) ON VIOLATION DROP ROW
  )
  COMMENT 'Raw card transactions as received from payment networks. One row per card swipe. raw_transaction_descriptor is the unstructured merchant string that must be enriched.'
AS SELECT
    CAST(transaction_id AS STRING)                     AS transaction_id,
    CAST(transaction_date AS STRING)                   AS transaction_date,
    CAST(transaction_amount AS DOUBLE)                 AS transaction_amount,
    CAST(currency AS STRING)                           AS currency,
    CAST(raw_transaction_descriptor AS STRING)         AS raw_transaction_descriptor,
    CAST(country AS STRING)                            AS country,
    CAST(payment_facilitator AS STRING)                AS payment_facilitator,
    _metadata.file_path                                AS _source_file,
    current_timestamp()                                AS _ingested_at
FROM STREAM read_files(
    '/Volumes/serverless_stable_iczfn0_catalog/febar/raw_landing/transactions',
    format           => 'csv',
    header           => true,
    inferColumnTypes => true,
    schemaHints      => 'transaction_amount double'
);


CREATE OR REFRESH STREAMING TABLE bronze_merchants
  (
    CONSTRAINT valid_merchant_id EXPECT (merchant_id IS NOT NULL) ON VIOLATION DROP ROW,
    CONSTRAINT has_name          EXPECT (merchant_name IS NOT NULL) ON VIOLATION DROP ROW
  )
  COMMENT 'Raw canonical merchant reference records (name, address, category, contact). Source of truth for merchant identities.'
AS SELECT
    CAST(merchant_id AS STRING)        AS merchant_id,
    CAST(merchant_name AS STRING)      AS merchant_name,
    CAST(address AS STRING)            AS address,
    CAST(city AS STRING)               AS city,
    CAST(state AS STRING)              AS state,
    CAST(country AS STRING)            AS country,
    CAST(postal_code AS STRING)        AS postal_code,
    CAST(merchant_category AS STRING)  AS merchant_category,
    CAST(website AS STRING)            AS website,
    CAST(phone_number AS STRING)       AS phone_number,
    _metadata.file_path                AS _source_file,
    current_timestamp()                AS _ingested_at
FROM STREAM read_files(
    '/Volumes/serverless_stable_iczfn0_catalog/febar/raw_landing/merchants',
    format           => 'csv',
    header           => true,
    inferColumnTypes => true
);


CREATE OR REFRESH STREAMING TABLE bronze_merchant_aliases
  (
    CONSTRAINT valid_alias_id EXPECT (alias_id IS NOT NULL) ON VIOLATION DROP ROW,
    CONSTRAINT linked         EXPECT (merchant_id IS NOT NULL) ON VIOLATION DROP ROW
  )
  COMMENT 'Raw alternative merchant names (abbreviations, legal names, DBA, facilitator-prefixed forms) mapped to canonical merchant_id.'
AS SELECT
    CAST(alias_id AS STRING)     AS alias_id,
    CAST(merchant_id AS STRING)  AS merchant_id,
    CAST(alias_name AS STRING)   AS alias_name,
    CAST(alias_type AS STRING)   AS alias_type,
    _metadata.file_path          AS _source_file,
    current_timestamp()          AS _ingested_at
FROM STREAM read_files(
    '/Volumes/serverless_stable_iczfn0_catalog/febar/raw_landing/merchant_aliases',
    format           => 'csv',
    header           => true,
    inferColumnTypes => true
);
