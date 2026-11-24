"""Create the Databricks Vector Search index over canonical merchants.

Pipeline:
  1. Build a CDF-enabled Delta source table `silver_merchants_embedding` from the
     governed `gold_merchants` table. Its `embedding_text` column concatenates
     merchant name + aliases + location + category (prepared in the Silver layer).
  2. Create a Delta Sync index with Databricks-managed embeddings
     (`databricks-gte-large-en`) on `embedding_text`.
  3. Trigger a sync and poll until the index is ONLINE.

Idempotent: re-running refreshes the source table and re-syncs the index.

Run:  PYTHONPATH=. python3 vector_search/create_index.py
"""
from __future__ import annotations

import json
import subprocess
import time

from common.config import CFG
from common.dbx import run_sql

ENDPOINT = CFG.vector_search["endpoint_name"]
INDEX = CFG.vector_search["index_name"]
SOURCE = CFG.vector_search["source_table"]
PK = CFG.vector_search["primary_key"]
EMB_COL = CFG.vector_search["embedding_source_column"]
EMB_MODEL = CFG.models["embedding_endpoint"]


def _cli_json(args: list[str], tolerate_errors: bool = False) -> dict:
    cmd = ["databricks", *args, "--profile", CFG.profile]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "").strip()
    if p.returncode != 0 and not out:
        if tolerate_errors:
            return {"_error": p.stderr.strip()}
        raise RuntimeError(f"CLI failed: {' '.join(cmd)}\n{p.stderr}")
    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        return {"_raw": out, "_stderr": p.stderr}


def build_source_table():
    print(f"[1/3] building CDF source table {SOURCE} from gold_merchants ...")
    # Create once (preserving table identity so the Vector Search CDF feed is not
    # invalidated), then refresh contents with INSERT OVERWRITE. Using
    # CREATE OR REPLACE would create a new table identity and break an existing
    # Delta Sync index's change feed.
    run_sql(f"""
        CREATE TABLE IF NOT EXISTS {SOURCE} (
            merchant_id STRING, merchant_name STRING, address STRING, city STRING,
            state STRING, country STRING, postal_code STRING, merchant_category STRING,
            website STRING, {EMB_COL} STRING
        ) TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """)
    run_sql(f"""
        INSERT OVERWRITE {SOURCE}
        SELECT merchant_id, merchant_name, address, city, state, country,
               postal_code, merchant_category, website, {EMB_COL}
        FROM {CFG.table('gold_merchants')}
    """)
    n = run_sql(f"SELECT count(*) AS n FROM {SOURCE}")
    cnt = n["result"]["data_array"][0][0]
    print(f"      source rows: {cnt}")


def create_index():
    print(f"[2/3] creating Delta Sync index {INDEX} (managed embeddings: {EMB_MODEL}) ...")
    existing = _cli_json(["vector-search-indexes", "get-index", INDEX], tolerate_errors=True)
    if existing.get("name") == INDEX:
        print("      index already exists — triggering sync")
        _cli_json(["vector-search-indexes", "sync-index", INDEX])
        return
    spec = {
        "name": INDEX,
        "endpoint_name": ENDPOINT,
        "primary_key": PK,
        "index_type": "DELTA_SYNC",
        "delta_sync_index_spec": {
            "source_table": SOURCE,
            "pipeline_type": "TRIGGERED",
            "embedding_source_columns": [
                {"name": EMB_COL, "embedding_model_endpoint_name": EMB_MODEL}
            ],
        },
    }
    res = _cli_json(["vector-search-indexes", "create-index", "--json", json.dumps(spec)])
    print("      create response:", json.dumps(res)[:300])


def wait_online(timeout_s: int = 1200):
    print("[3/3] waiting for index to be ready ...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        idx = _cli_json(["vector-search-indexes", "get-index", INDEX], tolerate_errors=True)
        if idx.get("_error"):
            # transient (e.g. IP ACL) — keep polling
            print(f"      (transient: {idx['_error'][:80]})")
            time.sleep(20)
            continue
        status = idx.get("status", {})
        ready = bool(status.get("ready", False))
        indexed = status.get("indexed_row_count", "?")
        print(f"      ready={ready} indexed_rows={indexed}")
        if ready:
            print("      INDEX READY")
            return idx
        time.sleep(20)
    raise TimeoutError("Vector Search index did not become ready in time")


if __name__ == "__main__":
    build_source_table()
    create_index()
    wait_online()
