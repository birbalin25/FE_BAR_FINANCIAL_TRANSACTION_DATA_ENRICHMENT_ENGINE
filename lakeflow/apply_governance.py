"""Apply Unity Catalog governance (table + column descriptions) to the
pipeline-produced tables.

Materialized views created via `CREATE OR REFRESH` do not re-apply inline column
comments when the object already exists, so we apply them idempotently here with
`COMMENT ON COLUMN`. Safe to re-run after any pipeline refresh.

Run:  python lakeflow/apply_governance.py
"""
from __future__ import annotations

from common.config import CFG
from common.dbx import run_sql

# (table, {column: comment})
COLUMN_COMMENTS: dict[str, dict[str, str]] = {
    "bronze_transactions": {
        "transaction_id": "Unique transaction identifier (primary key).",
        "raw_transaction_descriptor": "Unstructured merchant descriptor as received from the payment network.",
        "payment_facilitator": "Raw payment-facilitator hint from the feed (may be UNKNOWN).",
    },
    "bronze_merchants": {
        "merchant_id": "Canonical unique merchant identifier (primary key).",
        "merchant_name": "Canonical merchant name.",
    },
    "bronze_merchant_aliases": {
        "alias_id": "Unique alias identifier (primary key).",
        "merchant_id": "Canonical merchant this alias maps to (foreign key).",
        "alias_name": "Alternative merchant name (abbreviation, legal, DBA, facilitator form).",
    },
    "silver_transactions": {
        "transaction_id": "Unique transaction identifier (primary key).",
        "raw_transaction_descriptor": "Original unstructured descriptor, preserved for traceability.",
        "normalized_descriptor": "Whitespace-normalized, upper-cased descriptor.",
    },
    "silver_merchants": {
        "merchant_id": "Canonical unique merchant identifier (primary key).",
        "embedding_text": "Prepared embedding input: name + aliases + location + category.",
        "alias_count": "Count of known aliases for this merchant.",
    },
    "gold_transactions": {
        "transaction_id": "Unique transaction identifier (primary key).",
        "transaction_ts": "Transaction timestamp.",
        "transaction_date": "Transaction calendar date.",
        "transaction_month": "Month bucket (first day of month) for time-series analytics.",
        "transaction_amount": "Transaction amount in the transaction currency.",
        "currency": "ISO currency code.",
        "country": "Country where the transaction occurred.",
        "raw_facilitator_hint": "Payment-facilitator hint from the raw feed (may be UNKNOWN); authoritative facilitator comes from LLM extraction.",
        "raw_transaction_descriptor": "Original unstructured merchant descriptor as received from the payment network.",
        "normalized_descriptor": "Whitespace-normalized, upper-cased descriptor for display.",
    },
    "gold_merchants": {
        "merchant_id": "Canonical unique merchant identifier (primary key).",
        "merchant_name": "Canonical merchant display name.",
        "address": "Street address of the merchant location.",
        "city": "Merchant city (title-cased).",
        "state": "Merchant state (upper-cased 2-letter code).",
        "country": "Merchant country.",
        "postal_code": "Merchant postal / ZIP code.",
        "merchant_category": "Merchant business category (e.g. Coffee Shop, Grocery, Gas Station).",
        "website": "Merchant website URL.",
        "phone_number": "Merchant contact phone number.",
        "alias_count": "Number of known alternative names (aliases) for this merchant.",
        "embedding_text": "Concatenated text (name + aliases + location + category) used to generate the Vector Search embedding.",
    },
    "gold_transaction_volume_metrics": {
        "transaction_month": "Month bucket.",
        "raw_facilitator_hint": "Raw facilitator hint from the feed.",
        "transaction_count": "Number of transactions in the month/facilitator bucket.",
        "total_amount": "Sum of transaction amounts.",
        "avg_amount": "Average transaction amount.",
    },
}


def main():
    applied = 0
    for table, cols in COLUMN_COMMENTS.items():
        fq = CFG.table(table)
        for col, comment in cols.items():
            safe = comment.replace("'", "''")
            run_sql(f"COMMENT ON COLUMN {fq}.{col} IS '{safe}'")
            applied += 1
        print(f"  governed {table}: {len(cols)} columns")
    print(f"Applied {applied} column comments across {len(COLUMN_COMMENTS)} tables.")


if __name__ == "__main__":
    main()
