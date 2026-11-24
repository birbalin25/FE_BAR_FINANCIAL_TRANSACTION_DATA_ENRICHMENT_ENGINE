"""Populate Lakebase with realistic operational volume by enriching a sample of
transactions and persisting each result (with mapping reuse + auto-confirm).

This is the data that powers the operations dashboard, the UC Gold sync, and the
Genie space. Idempotent: transactions already persisted are skipped.

Run:  PYTHONPATH=. python3 scripts/batch_enrich_persist.py [--n 400] [--workers 8]
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.config import CFG
from common.dbx import rows
from common.ops import enrich_and_persist
from lakebase import persistence as lb

T = f"{CFG.catalog}.{CFG.schema}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    lb.init_schema()
    existing = {r["transaction_id"] for r in
                lb.q("SELECT DISTINCT transaction_id FROM merchant_enrichment_results", fetch=True) or []}

    # deterministic sample across the transaction population
    sample = rows(f"""
        SELECT transaction_id, raw_transaction_descriptor AS descriptor
        FROM {T}.gold_transactions
        WHERE pmod(hash(transaction_id), 20) = 0        -- ~1/20 deterministic sample
        ORDER BY transaction_id
        LIMIT {args.n}
    """)
    todo = [r for r in sample if r["transaction_id"] not in existing]
    print(f"{len(sample)} sampled, {len(todo)} to enrich ({len(existing)} already present)")

    t0 = time.time()
    done = 0
    def work(r):
        return enrich_and_persist(r["descriptor"], transaction_id=r["transaction_id"])
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001
                print("  error:", repr(e)[:120])
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(todo)} ({time.time()-t0:.0f}s)")

    import json
    print(f"done in {time.time()-t0:.0f}s")
    print("dashboard:", json.dumps(lb.dashboard_metrics(), default=str))


if __name__ == "__main__":
    main()
