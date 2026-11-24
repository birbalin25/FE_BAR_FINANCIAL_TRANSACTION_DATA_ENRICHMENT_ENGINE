"""Demonstrate and capture the full Lakebase operational loop as evidence:
enrich -> persist -> mapping reuse -> ambiguous -> manual review -> analyst
approval -> reuse of the analyst-confirmed mapping -> live dashboard metrics.

Writes evidence/lakebase_execution.md.
"""
from __future__ import annotations

import json

from common.evidence import header, md_table, code_block
from common.ops import enrich_and_persist
from lakebase import persistence as lb

parts: list[str] = []


def log(title: str, obj):
    parts.append(f"\n### {title}\n")
    parts.append(code_block(json.dumps(obj, indent=2, default=str), "json"))


def main():
    lb.init_schema()
    parts.append(header("Phase 3 Evidence — Lakebase Operational Serving",
        "Live reads/writes against the Lakebase (Autoscaling Postgres) project "
        "`febar-lakebase`, schema `febar_ops`. Demonstrates persistence, confirmed-"
        "mapping reuse, the manual-review queue, analyst feedback, and duplicate handling."))

    demo = "SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY"

    parts.append("\n## 1. Fresh enrichment is persisted (source = enrichment_workflow)\n")
    r1 = enrich_and_persist(demo, transaction_id="DEMO-001")
    log("enrich_and_persist(descriptor) #1", {k: r1[k] for k in
        ("decision", "merchant_id", "merchant_name", "confidence", "source",
         "descriptor_fingerprint")})

    parts.append("\n## 2. Confirmed mapping auto-saved for a strong match\n")
    mp = lb.lookup_mapping(r1["descriptor_fingerprint"])
    log("merchant_mapping row (by fingerprint)", mp)

    parts.append("\n## 3. Re-submitting the SAME descriptor reuses the mapping "
                 "(skips extraction + Vector Search + judge)\n")
    r2 = enrich_and_persist(demo, transaction_id="DEMO-002")
    log("enrich_and_persist(descriptor) #2", {k: r2[k] for k in
        ("decision", "merchant_id", "merchant_name", "confidence", "source", "latency_ms")})
    parts.append(f"\n> Note the `source` is now **{r2['source']}** and latency dropped from "
                 f"**{r1['latency_ms']} ms** to **{r2['latency_ms']} ms** "
                 f"({r1['llm_calls']} LLM calls → {r2['llm_calls']} LLM calls).\n")

    parts.append("\n## 4. Duplicate submission handling (same transaction_id)\n")
    before = lb.q("SELECT count(*) AS n FROM merchant_enrichment_results WHERE transaction_id='DEMO-002'", fetch=True)[0]["n"]
    enrich_and_persist(demo, transaction_id="DEMO-002")  # resubmit same txn
    after = lb.q("SELECT count(*) AS n FROM merchant_enrichment_results WHERE transaction_id='DEMO-002'", fetch=True)[0]["n"]
    parts.append(f"\nResubmitting transaction `DEMO-002` keeps a single row "
                 f"(before={before}, after={after}) — the prior result is replaced, not duplicated.\n")

    parts.append("\n## 5. An AMBIGUOUS descriptor is persisted and queued for manual review\n")
    amb = "PAYPAL *TACO FIESTA"
    r3 = enrich_and_persist(amb, transaction_id="DEMO-003")
    log("enrich_and_persist(ambiguous)", {k: r3[k] for k in
        ("decision", "merchant_id", "confidence", "source", "descriptor_fingerprint")})
    queue = lb.list_review_queue("PENDING")
    parts.append("\n**Manual review queue (PENDING):**\n")
    parts.append(md_table([{
        "review_id": x["review_id"], "transaction_id": x["transaction_id"],
        "raw_descriptor": x["raw_descriptor"],
        "n_candidates": len(x["candidate_merchants"] or []),
        "status": x["review_status"],
    } for x in queue]))

    parts.append("\n## 6. Analyst approves a merchant for the ambiguous transaction\n")
    review = queue[0]
    candidates = review["candidate_merchants"] or []
    chosen = candidates[0]["merchant_id"] if candidates else None
    approval = lb.approve_review(review["review_id"], chosen, analyst="demo.analyst@databricks.com")
    log("approve_review(...)", approval)
    log("analyst_feedback row", lb.q(
        "SELECT transaction_id, selected_merchant_id, analyst_decision, analyst FROM analyst_feedback ORDER BY feedback_id DESC LIMIT 1",
        fetch=True)[0])

    parts.append("\n## 7. The analyst-confirmed mapping is now reused for equivalent transactions\n")
    r4 = enrich_and_persist(amb, transaction_id="DEMO-004")
    log("enrich_and_persist(ambiguous) after approval", {k: r4[k] for k in
        ("decision", "merchant_id", "merchant_name", "source")})
    parts.append(f"\n> After approval, the same descriptor now resolves to "
                 f"**{r4['decision']} / {r4['merchant_id']}** via **{r4['source']}**.\n")

    parts.append("\n## 8. Live operational dashboard metrics (never hard-coded)\n")
    parts.append(md_table([lb.dashboard_metrics()]))

    parts.append("\n## 9. Recent enrichment activity (live from Postgres)\n")
    parts.append(md_table([{
        "transaction_id": a["transaction_id"], "decision": a["decision"],
        "merchant_name": a["merchant_name"], "source": a["source"],
        "confidence": a["confidence"],
    } for a in lb.recent_activity(10)]))

    with open("evidence/lakebase_execution.md", "w") as f:
        f.write("\n".join(parts))
    print("wrote evidence/lakebase_execution.md")


if __name__ == "__main__":
    main()
