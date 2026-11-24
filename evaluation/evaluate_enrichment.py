"""Evaluate the enrichment engine against the held-out ground truth.

Runs the full workflow over every evaluation transaction (concurrently),
computes entity-recognition / retrieval / linkage / operational metrics, logs
them to MLflow, writes the `gold_enrichment_quality_metrics` Unity Catalog
table, and emits evidence/evaluation_results.md.

Ground truth is used ONLY here for scoring and is never passed into enrichment.

Run:  PYTHONPATH=. python3 evaluation/evaluate_enrichment.py [--limit N] [--workers K]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from common.config import CFG
from common.dbx import rows, run_sql
from common.enrichment_service import enrich
from common.evidence import header, md_table

T = f"{CFG.catalog}.{CFG.schema}"
KNOWN_FACILITATORS = {"square", "paypal", "stripe", "toast", "clover", "venmo"}


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _tokens(s: str | None) -> set[str]:
    return {t for t in _norm(s).split() if t}


def name_matches(extracted: str | None, expected: str | None) -> bool:
    et, xt = _tokens(extracted), _tokens(expected)
    if not xt:
        return False
    if not et:
        return False
    inter = et & xt
    jacc = len(inter) / len(et | xt)
    # correct if names overlap substantially or extracted is contained in expected
    return jacc >= 0.5 or (len(inter) >= 1 and inter >= (xt & et) and next(iter(sorted(xt))) in et)


def load_eval(limit: int | None) -> list[dict]:
    q = f"""
        SELECT g.transaction_id, t.raw_transaction_descriptor AS descriptor,
               g.expected_decision, g.expected_merchant_id, g.expected_merchant_name,
               g.expected_payment_facilitator, g.expected_city, g.expected_state
        FROM {T}.eval_ground_truth g
        JOIN {T}.gold_transactions t USING (transaction_id)
        ORDER BY g.transaction_id
    """
    data = rows(q)
    return data[:limit] if limit else data


def run_one(row: dict) -> dict:
    r = enrich(row["descriptor"], transaction_id=row["transaction_id"])
    cand_ids = [c["merchant_id"] for c in r["candidates"]]
    ent = r["extracted_entities"] or {}
    return {
        "transaction_id": row["transaction_id"],
        "descriptor": row["descriptor"],
        "expected_decision": row["expected_decision"],
        "expected_merchant_id": row["expected_merchant_id"] or None,
        "expected_merchant_name": row["expected_merchant_name"] or None,
        "expected_facilitator": row["expected_payment_facilitator"] or None,
        "expected_city": row["expected_city"] or None,
        "expected_state": row["expected_state"] or None,
        "got_decision": r["decision"],
        "got_merchant_id": r["merchant_id"],
        "confidence": r["confidence"],
        "candidate_ids": cand_ids,
        "ext_facilitator": ent.get("payment_facilitator"),
        "ext_merchant_name": ent.get("merchant_name"),
        "ext_city": ent.get("city"),
        "ext_state": ent.get("state"),
        "latency_ms": r.get("latency_ms"),
        "llm_calls": r.get("llm_calls", 0),
    }


def compute_metrics(res: list[dict]) -> dict:
    n = len(res)
    truth_matched = [r for r in res if r["expected_decision"] == "MATCHED"]
    truth_nomatch = [r for r in res if r["expected_decision"] == "NO_MATCH"]
    truth_ambig = [r for r in res if r["expected_decision"] == "AMBIGUOUS"]

    # --- entity recognition ---
    fac_rows = [r for r in res if (r["expected_facilitator"] or "").lower() in KNOWN_FACILITATORS]
    fac_ok = sum(1 for r in fac_rows
                 if (r["ext_facilitator"] or "").lower() == (r["expected_facilitator"] or "").lower())
    name_ok = sum(1 for r in truth_matched if name_matches(r["ext_merchant_name"], r["expected_merchant_name"]))
    loc_rows = [r for r in truth_matched if r["expected_city"]]
    loc_ok = sum(1 for r in loc_rows
                 if _norm(r["ext_city"]) == _norm(r["expected_city"])
                 and _norm(r["ext_state"]) == _norm(r["expected_state"]))

    # --- retrieval: Recall@10 over truth-MATCHED (expected id present) ---
    recall_rows = [r for r in truth_matched if r["expected_merchant_id"]]
    recall_hits = sum(1 for r in recall_rows if r["expected_merchant_id"] in r["candidate_ids"])

    # --- linkage precision / recall / FP ---
    sys_matched = [r for r in res if r["got_decision"] == "MATCHED"]
    tp = sum(1 for r in sys_matched
             if r["expected_decision"] == "MATCHED" and r["got_merchant_id"] == r["expected_merchant_id"])
    fp = len(sys_matched) - tp
    precision = tp / len(sys_matched) if sys_matched else 0.0
    recall = tp / len(truth_matched) if truth_matched else 0.0
    fp_rate = fp / len(sys_matched) if sys_matched else 0.0
    # forced matches on non-matchable truths (ambiguous/no-match that system called MATCHED)
    forced = sum(1 for r in sys_matched if r["expected_decision"] in ("NO_MATCH", "AMBIGUOUS"))

    nomatch_acc = (sum(1 for r in truth_nomatch if r["got_decision"] == "NO_MATCH")
                   / len(truth_nomatch)) if truth_nomatch else 0.0
    ambig_acc = (sum(1 for r in truth_ambig if r["got_decision"] == "AMBIGUOUS")
                 / len(truth_ambig)) if truth_ambig else 0.0

    # --- operational ---
    sys_ambiguous = [r for r in res if r["got_decision"] == "AMBIGUOUS"]
    manual_review_rate = len(sys_ambiguous) / n if n else 0.0
    enrichment_success_rate = len(sys_matched) / n if n else 0.0
    avg_latency = sum(r["latency_ms"] or 0 for r in res) / n if n else 0.0
    llm_calls = sum(r["llm_calls"] for r in res)

    def pct(x):
        return round(100 * x, 2)

    return {
        "total_test_transactions": n,
        "facilitator_extraction_accuracy": pct(fac_ok / len(fac_rows)) if fac_rows else None,
        "merchant_name_extraction_accuracy": pct(name_ok / len(truth_matched)) if truth_matched else None,
        "location_extraction_accuracy": pct(loc_ok / len(loc_rows)) if loc_rows else None,
        "recall_at_10": pct(recall_hits / len(recall_rows)) if recall_rows else None,
        "pct_correct_merchant_not_retrieved": pct(1 - recall_hits / len(recall_rows)) if recall_rows else None,
        "matching_precision": pct(precision),
        "matching_recall": pct(recall),
        "false_positive_rate": pct(fp_rate),
        "forced_matches_on_nonmatchable": forced,
        "no_match_classification_accuracy": pct(nomatch_acc),
        "ambiguous_classification_accuracy": pct(ambig_acc),
        "enrichment_success_rate": pct(enrichment_success_rate),
        "manual_review_rate": pct(manual_review_rate),
        "avg_latency_ms": round(avg_latency, 1),
        "total_llm_invocations": llm_calls,
        "_counts": {"truth_matched": len(truth_matched), "truth_no_match": len(truth_nomatch),
                    "truth_ambiguous": len(truth_ambig), "system_matched": len(sys_matched),
                    "true_positives": tp, "false_positives": fp,
                    "recall_denom": len(recall_rows), "recall_hits": recall_hits},
    }


def write_quality_table(m: dict):
    run_sql(f"""
        CREATE TABLE IF NOT EXISTS {T}.gold_enrichment_quality_metrics (
            evaluation_date       DATE    COMMENT 'Date the evaluation run was executed.',
            total_test_transactions INT   COMMENT 'Number of held-out transactions evaluated.',
            recall_at_10          DOUBLE  COMMENT 'Percent of matchable transactions whose correct merchant is in the Vector Search top-10.',
            matching_precision    DOUBLE  COMMENT 'Percent of system MATCHED decisions that are correct.',
            matching_recall       DOUBLE  COMMENT 'Percent of truly-matchable transactions the system correctly matched.',
            false_positive_rate   DOUBLE  COMMENT 'Percent of system MATCHED decisions that are incorrect (primary risk metric).'
        ) COMMENT 'Enrichment quality metrics per evaluation run (populated by evaluation/evaluate_enrichment.py).'
    """)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_sql(f"DELETE FROM {T}.gold_enrichment_quality_metrics WHERE evaluation_date = '{today}'")
    run_sql(f"""
        INSERT INTO {T}.gold_enrichment_quality_metrics VALUES (
            '{today}', {m['total_test_transactions']}, {m['recall_at_10']},
            {m['matching_precision']}, {m['matching_recall']}, {m['false_positive_rate']}
        )
    """)


def log_mlflow(m: dict, res: list[dict]):
    try:
        import mlflow
        mlflow.set_tracking_uri("databricks")
        mlflow.set_experiment("/Users/birbal.das@databricks.com/febar_eval")
        with mlflow.start_run(run_name=f"enrichment_eval_{datetime.now():%Y%m%d_%H%M%S}"):
            mlflow.log_params({
                "chat_endpoint": CFG.models["chat_endpoint"],
                "embedding_endpoint": CFG.models["embedding_endpoint"],
                "vector_search_index": CFG.vector_search["index_name"],
                "top_k": CFG.vector_search["top_k"],
                "match_confidence_threshold": 0.70,
                "n_eval": m["total_test_transactions"],
            })
            mlflow.log_metrics({k: v for k, v in m.items()
                                if isinstance(v, (int, float)) and not k.startswith("_")})
            # sample of extraction+linkage inputs/outputs as an artifact
            sample = res[:40]
            with open("/tmp/febar_eval_sample.json", "w") as f:
                json.dump(sample, f, indent=2, default=str)
            mlflow.log_artifact("/tmp/febar_eval_sample.json")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  (MLflow logging skipped: {repr(e)[:160]})")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    data = load_eval(args.limit)
    print(f"evaluating {len(data)} transactions with {args.workers} workers ...")
    t0 = time.time()
    res: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, row): row for row in data}
        done = 0
        for fut in as_completed(futs):
            res.append(fut.result())
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(data)} done ({time.time()-t0:.0f}s)")
    res.sort(key=lambda r: r["transaction_id"])
    wall = time.time() - t0

    m = compute_metrics(res)
    print(json.dumps({k: v for k, v in m.items() if k != "_counts"}, indent=2))

    write_quality_table(m)
    mlflow_ok = log_mlflow(m, res)

    # evidence markdown
    parts = [header("Phase 6 Evidence — Enrichment Evaluation (vs. held-out ground truth)",
                    f"Full evaluation over {m['total_test_transactions']} held-out transactions. "
                    f"Models: chat `{CFG.models['chat_endpoint']}`, embeddings "
                    f"`{CFG.models['embedding_endpoint']}`. Wall time {wall:.0f}s. "
                    f"MLflow logged: {mlflow_ok}.")]
    parts.append("## Entity recognition accuracy\n")
    parts.append(md_table([
        {"metric": "Payment-facilitator extraction accuracy", "value %": m["facilitator_extraction_accuracy"]},
        {"metric": "Merchant-name extraction accuracy", "value %": m["merchant_name_extraction_accuracy"]},
        {"metric": "Location (city+state) extraction accuracy", "value %": m["location_extraction_accuracy"]},
    ]))
    parts.append("\n## Candidate retrieval (Vector Search)\n")
    parts.append(md_table([
        {"metric": "Recall@10", "value %": m["recall_at_10"]},
        {"metric": "Correct merchant NOT retrieved", "value %": m["pct_correct_merchant_not_retrieved"]},
    ]))
    parts.append("\n## Entity linkage (LLM judge)\n")
    parts.append(md_table([
        {"metric": "Matching precision", "value %": m["matching_precision"]},
        {"metric": "Matching recall", "value %": m["matching_recall"]},
        {"metric": "False-positive rate (wrong MATCHED / all MATCHED)", "value %": m["false_positive_rate"]},
        {"metric": "Forced matches on non-matchable truths (count)", "value %": m["forced_matches_on_nonmatchable"]},
        {"metric": "NO_MATCH classification accuracy", "value %": m["no_match_classification_accuracy"]},
        {"metric": "AMBIGUOUS classification accuracy", "value %": m["ambiguous_classification_accuracy"]},
    ]))
    parts.append("\n## Operational metrics\n")
    parts.append(md_table([
        {"metric": "Enrichment success rate (system MATCHED)", "value": f"{m['enrichment_success_rate']}%"},
        {"metric": "Manual review rate (system AMBIGUOUS)", "value": f"{m['manual_review_rate']}%"},
        {"metric": "Avg end-to-end latency", "value": f"{m['avg_latency_ms']} ms"},
        {"metric": "Total LLM invocations", "value": m["total_llm_invocations"]},
    ]))
    parts.append("\n## Confusion detail (counts)\n")
    parts.append(code_block := md_table([m["_counts"]]))
    with open("evidence/evaluation_results.md", "w") as f:
        f.write("\n".join(parts))
    print("wrote evidence/evaluation_results.md and gold_enrichment_quality_metrics table")


if __name__ == "__main__":
    main()
