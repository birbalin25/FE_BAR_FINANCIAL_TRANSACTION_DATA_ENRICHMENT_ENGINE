-- ============================================================================
-- Lakebase (Postgres) operational schema for the Merchant Enrichment Engine
-- ----------------------------------------------------------------------------
-- These tables back the Databricks App's operational reads/writes: enrichment
-- results, confirmed-mapping reuse, the manual-review queue, and analyst
-- feedback. Applied by lakebase/persistence.py (init_schema).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS febar_ops;

-- A) Every enrichment result (one row per processed transaction submission)
CREATE TABLE IF NOT EXISTS febar_ops.merchant_enrichment_results (
    id                   BIGSERIAL PRIMARY KEY,
    transaction_id       TEXT,
    raw_descriptor       TEXT NOT NULL,
    descriptor_fingerprint TEXT NOT NULL,
    extracted_entities   JSONB,
    merchant_id          TEXT,
    merchant_name        TEXT,
    decision             TEXT NOT NULL CHECK (decision IN ('MATCHED','NO_MATCH','AMBIGUOUS')),
    confidence           DOUBLE PRECISION,
    reason               TEXT,
    source               TEXT,            -- mapping_reuse | enrichment_workflow
    candidates           JSONB,
    processed_timestamp  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_enrich_fp   ON febar_ops.merchant_enrichment_results (descriptor_fingerprint);
CREATE INDEX IF NOT EXISTS idx_enrich_txn  ON febar_ops.merchant_enrichment_results (transaction_id);
CREATE INDEX IF NOT EXISTS idx_enrich_dec  ON febar_ops.merchant_enrichment_results (decision);

-- B) Confirmed descriptor -> merchant mappings used for reuse (fingerprint key)
CREATE TABLE IF NOT EXISTS febar_ops.merchant_mapping (
    descriptor_fingerprint TEXT PRIMARY KEY,
    merchant_id          TEXT NOT NULL,
    merchant_name        TEXT,
    confidence           DOUBLE PRECISION,
    mapping_status       TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK (mapping_status IN ('CONFIRMED')),
    confirmed_timestamp  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- C) Manual-review queue for AMBIGUOUS transactions
CREATE TABLE IF NOT EXISTS febar_ops.manual_review_queue (
    review_id            BIGSERIAL PRIMARY KEY,
    transaction_id       TEXT,
    raw_descriptor       TEXT NOT NULL,
    descriptor_fingerprint TEXT NOT NULL,
    extracted_entities   JSONB,
    candidate_merchants  JSONB,
    review_status        TEXT NOT NULL DEFAULT 'PENDING' CHECK (review_status IN ('PENDING','APPROVED','REJECTED')),
    created_timestamp    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_review_status ON febar_ops.manual_review_queue (review_status);

-- D) Analyst feedback / decisions on reviewed transactions
CREATE TABLE IF NOT EXISTS febar_ops.analyst_feedback (
    feedback_id          BIGSERIAL PRIMARY KEY,
    transaction_id       TEXT,
    review_id            BIGINT,
    descriptor_fingerprint TEXT,
    selected_merchant_id TEXT,
    analyst_decision     TEXT NOT NULL CHECK (analyst_decision IN ('APPROVED','REJECTED')),
    analyst             TEXT,
    feedback_timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);
