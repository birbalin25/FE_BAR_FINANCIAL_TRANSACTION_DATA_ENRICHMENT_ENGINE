"""Create and configure the actual Databricks Genie space for merchant-enrichment
analytics, via the Genie Spaces REST API (POST /api/2.0/genie/spaces).

Configures:
  * data sources  -> the 3 Unity Catalog Gold tables (with table descriptions)
  * instructions  -> business definitions + metric definitions + routing guidance
  * sample questions -> the 8 required business questions

Writes the created space_id back into config/resources.json.

Run:  PYTHONPATH=. python3 genie/create_genie_space.py
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from common.config import CFG

T = f"{CFG.catalog}.{CFG.schema}"
WAREHOUSE_ID = CFG.databricks["warehouse_id"]
PARENT_PATH = "/Workspace/Users/birbal.das@databricks.com"
TITLE = CFG.genie["space_title"]
DESCRIPTION = CFG.genie["description"]

TABLES = [
    (f"{T}.gold_enrichment_results",
     "Per-transaction merchant enrichment outcomes. One row per processed transaction with its "
     "decision (MATCHED/NO_MATCH/AMBIGUOUS), matched merchant, confidence, extracted payment "
     "facilitator, merchant category, and processed timestamp. PRIMARY table for questions about "
     "enrichment volumes, success/unmatched rates, facilitators, categories, and trends over time."),
    (f"{T}.gold_merchant_metrics",
     "Per-merchant enrichment volume metrics: how many transactions were matched to each canonical "
     "merchant, with merchant category. Use for 'which merchants have the highest transaction volumes'."),
    (f"{T}.gold_enrichment_quality_metrics",
     "Model quality metrics per evaluation run: recall_at_10, matching_precision, matching_recall, "
     "false_positive_rate, and total_test_transactions, measured against held-out ground truth. Use "
     "for questions about model accuracy, precision, recall, Recall@10, and false positives."),
]

INSTRUCTIONS = [
    "DOMAIN: This Genie space answers questions for the Payments Operations team of a retail bank "
    "about 'merchant enrichment' — the process of turning messy card-transaction descriptors "
    "(e.g. 'SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY') into standardized merchant identities.",

    "DECISIONS: Every transaction gets one decision. MATCHED = reliably linked to exactly one "
    "canonical merchant. NO_MATCH = no candidate merchant could be reliably linked. AMBIGUOUS = "
    "multiple merchants are plausible and the transaction is routed to analyst manual review. "
    "In gold_enrichment_results, decision IN ('MATCHED','NO_MATCH','AMBIGUOUS').",

    "ENRICHMENT SUCCESS RATE = count(decision='MATCHED') / count(*) over gold_enrichment_results, "
    "expressed as a percentage. UNMATCHED RATE = count(decision='NO_MATCH') / count(*). "
    "MANUAL REVIEW RATE = count(decision='AMBIGUOUS') / count(*). Transactions 'awaiting manual "
    "review' are the AMBIGUOUS transactions.",

    "PAYMENT FACILITATOR vs MERCHANT: the payment_facilitator (e.g. Square, PayPal, Stripe, Toast, "
    "Clover, Venmo) is the processor that routed the payment — it is NOT the merchant. The merchant "
    "is identified by merchant_id / merchant_name. 'Which facilitators generate the most ambiguous "
    "transactions' = group gold_enrichment_results by payment_facilitator where decision='AMBIGUOUS'.",

    "MODEL QUALITY: matching_precision, matching_recall, recall_at_10, and false_positive_rate come "
    "ONLY from gold_enrichment_quality_metrics (measured on held-out ground truth). Recall@10 is the "
    "percent of matchable transactions whose correct merchant was in the Vector Search top-10. "
    "False-positive rate is the percent of MATCHED decisions that were incorrect (the key risk metric).",

    "TABLE ROUTING: use gold_enrichment_results for decision counts, rates, facilitators, categories "
    "and time trends; gold_merchant_metrics for per-merchant transaction volumes; "
    "gold_enrichment_quality_metrics for precision/recall/Recall@10/false-positive accuracy metrics.",

    "TIME TRENDS: use processed_timestamp in gold_enrichment_results (e.g. date_trunc('day', "
    "processed_timestamp)) to show how enrichment success rate changes over time.",
]

QUESTIONS = [
    "How many transactions have been successfully enriched?",
    "What percentage of transactions remain unmatched?",
    "Which payment facilitators generate the most ambiguous transactions?",
    "Which merchant categories have the lowest matching accuracy?",
    "How many transactions are awaiting manual review?",
    "What is the overall merchant enrichment success rate?",
    "Which merchants have the highest transaction volumes?",
    "How has enrichment success rate changed over time?",
]


def _id() -> str:
    return uuid.uuid4().hex


def build_serialized_space() -> dict:
    return {
        "version": 2,
        "data_sources": {
            # the API requires tables sorted by identifier
            "tables": [{"identifier": ident, "description": [desc]}
                       for ident, desc in sorted(TABLES, key=lambda t: t[0])]
        },
        "instructions": {
            # the API allows at most one text_instruction: combine all guidance into one block
            "text_instructions": [{"id": _id(), "content": ["\n\n".join(INSTRUCTIONS)]}]
        },
        "config": {
            "sample_questions": sorted(
                [{"id": _id(), "question": [q]} for q in QUESTIONS], key=lambda x: x["id"])
        },
    }


def main():
    serialized = json.dumps(build_serialized_space())
    body = {
        "warehouse_id": WAREHOUSE_ID,
        "serialized_space": serialized,
        "title": TITLE,
        "description": DESCRIPTION,
        "parent_path": PARENT_PATH,
    }
    print("creating Genie space ...")
    p = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/genie/spaces", "--profile", CFG.profile,
         "--json", json.dumps(body)],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"create-space failed:\n{p.stderr}\n{p.stdout}")
    resp = json.loads(p.stdout)
    space_id = resp.get("space_id") or resp.get("id")
    print(f"created Genie space: {space_id}")
    print(json.dumps(resp, indent=2)[:500])

    # persist id into resources.json
    rp = Path(__file__).resolve().parent.parent / "config" / "resources.json"
    res = json.loads(rp.read_text())
    res["genie_space_id"] = space_id
    res["genie_space_url"] = f"{res['workspace_host']}/genie/rooms/{space_id}"
    rp.write_text(json.dumps(res, indent=2) + "\n")
    print(f"recorded space_id in {rp}")
    return space_id


if __name__ == "__main__":
    main()
