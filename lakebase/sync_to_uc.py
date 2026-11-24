"""Synchronize operational enrichment data from Lakebase (Postgres) into Unity
Catalog Gold analytics tables.

Lakebase is the operational system of record; Unity Catalog Gold is the governed
analytics surface that Genie queries. UC→Lakebase synced tables do NOT propagate
Lakebase writes back to UC, so we implement an explicit, re-runnable sync:

    Postgres -> local CSV -> UC Volume (staging) -> CREATE OR REPLACE Delta tables

Produces:
    gold_enrichment_results   (per-transaction enrichment outcomes)
    gold_merchant_metrics     (per-merchant matched volumes)

(gold_enrichment_quality_metrics is produced by evaluation/evaluate_enrichment.py.)

Run:  PYTHONPATH=. python3 lakebase/sync_to_uc.py
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

from common.config import CFG
from common.dbx import run_sql, scalar
from lakebase import persistence as lb

T = f"{CFG.catalog}.{CFG.schema}"
STAGE_DIR = f"/Volumes/{CFG.catalog}/{CFG.schema}/{CFG.unity_catalog['volume']}/sync_staging/enrichment_results"
STAGE_DBFS = f"dbfs:{STAGE_DIR}"


def _export_postgres_to_csv() -> Path:
    rows = lb.q("""
        SELECT transaction_id, raw_descriptor, merchant_id, merchant_name, decision,
               confidence,
               COALESCE(extracted_entities->>'payment_facilitator', '') AS payment_facilitator,
               to_char(processed_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS') AS processed_timestamp
        FROM merchant_enrichment_results
    """, fetch=True) or []
    tmp = Path(tempfile.gettempdir()) / "febar_enrichment_results.csv"
    fields = ["transaction_id", "raw_descriptor", "merchant_id", "merchant_name",
              "decision", "confidence", "payment_facilitator", "processed_timestamp"]
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    print(f"  exported {len(rows)} rows from Lakebase -> {tmp}")
    return tmp


def _upload(csv_path: Path):
    subprocess.run(["databricks", "fs", "mkdir", STAGE_DBFS, "--profile", CFG.profile],
                   capture_output=True, text=True)
    r = subprocess.run(["databricks", "fs", "cp", str(csv_path),
                        f"{STAGE_DBFS}/enrichment_results.csv", "--overwrite",
                        "--profile", CFG.profile], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"upload failed: {r.stderr}")
    print(f"  uploaded staging CSV -> {STAGE_DBFS}")


def _build_gold():
    # gold_enrichment_results (join category from canonical merchants for matched rows)
    run_sql(f"""
        CREATE OR REPLACE TABLE {T}.gold_enrichment_results
        COMMENT 'Per-transaction merchant enrichment outcomes, synced from Lakebase. Primary Genie analytics source for decisions/volumes.'
        AS
        WITH staged AS (
          SELECT
            CAST(transaction_id AS STRING)      AS transaction_id,
            CAST(raw_descriptor AS STRING)      AS raw_descriptor,
            CAST(merchant_id AS STRING)         AS merchant_id,
            CAST(merchant_name AS STRING)       AS merchant_name,
            CAST(decision AS STRING)            AS decision,
            CAST(confidence AS DOUBLE)          AS confidence,
            NULLIF(CAST(payment_facilitator AS STRING), '') AS payment_facilitator,
            CAST(processed_timestamp AS TIMESTAMP) AS processed_timestamp
          FROM read_files('{STAGE_DIR}', format => 'csv', header => true,
                          schemaHints => 'confidence double')
        )
        SELECT s.*, m.merchant_category
        FROM staged s
        LEFT JOIN {T}.gold_merchants m USING (merchant_id)
    """)
    # gold_merchant_metrics (per canonical merchant that received matches)
    run_sql(f"""
        CREATE OR REPLACE TABLE {T}.gold_merchant_metrics
        COMMENT 'Per-merchant enrichment volume metrics derived from gold_enrichment_results.'
        AS
        SELECT
            r.merchant_id,
            r.merchant_name,
            m.merchant_category,
            count(*)                                                     AS total_transactions,
            count_if(r.decision = 'MATCHED')                             AS matched_transactions,
            CAST(0 AS BIGINT)                                            AS unmatched_transactions,
            CAST(0 AS BIGINT)                                            AS ambiguous_transactions
        FROM {T}.gold_enrichment_results r
        LEFT JOIN {T}.gold_merchants m USING (merchant_id)
        WHERE r.merchant_id IS NOT NULL
        GROUP BY r.merchant_id, r.merchant_name, m.merchant_category
    """)


def _govern():
    cols = {
        "gold_enrichment_results": {
            "transaction_id": "Transaction identifier.",
            "raw_descriptor": "Original unstructured descriptor submitted for enrichment.",
            "merchant_id": "Canonical merchant matched (null for NO_MATCH / AMBIGUOUS).",
            "merchant_name": "Canonical merchant name (null unless MATCHED).",
            "decision": "Enrichment decision: MATCHED, NO_MATCH, or AMBIGUOUS.",
            "confidence": "Model confidence (0..1) in the decision.",
            "payment_facilitator": "Payment facilitator extracted from the descriptor (e.g. Square, PayPal).",
            "merchant_category": "Business category of the matched merchant.",
            "processed_timestamp": "When the transaction was enriched.",
        },
        "gold_merchant_metrics": {
            "merchant_id": "Canonical merchant identifier.",
            "merchant_name": "Canonical merchant name.",
            "merchant_category": "Merchant business category.",
            "total_transactions": "Total enrichment results attributed to this merchant.",
            "matched_transactions": "Transactions confidently MATCHED to this merchant.",
            "unmatched_transactions": "Not attributable per-merchant (tracked globally in gold_enrichment_results); 0 here.",
            "ambiguous_transactions": "Not attributable per-merchant (tracked globally in gold_enrichment_results); 0 here.",
        },
    }
    for table, c in cols.items():
        for col, comment in c.items():
            run_sql(f"COMMENT ON COLUMN {T}.{table}.{col} IS '{comment.replace(chr(39), chr(39)*2)}'")


def main():
    print("[1/4] exporting from Lakebase ...")
    csv_path = _export_postgres_to_csv()
    print("[2/4] uploading staging file to UC Volume ...")
    _upload(csv_path)
    print("[3/4] (re)building UC Gold analytics tables ...")
    _build_gold()
    print("[4/4] applying column governance ...")
    _govern()
    n1 = scalar(f"SELECT count(*) FROM {T}.gold_enrichment_results")
    n2 = scalar(f"SELECT count(*) FROM {T}.gold_merchant_metrics")
    print(f"synced: gold_enrichment_results={n1} rows, gold_merchant_metrics={n2} rows")


if __name__ == "__main__":
    main()
