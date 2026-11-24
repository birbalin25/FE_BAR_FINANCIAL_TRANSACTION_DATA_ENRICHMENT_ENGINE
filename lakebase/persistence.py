"""Lakebase (Postgres) operational persistence for the enrichment engine.

Provides the operational reads/writes the Databricks App needs:
  * persist_result()        - store an enrichment result (idempotent per txn)
  * lookup_mapping()        - confirmed-mapping reuse check (fingerprint key)
  * save_confirmed_mapping()
  * enqueue_review()/list_review_queue()/approve_review()/reject_review()
  * dashboard_metrics()     - live operational counters

Authentication uses short-lived Databricks OAuth tokens as the Postgres password
(sslmode=require). Token acquisition is pluggable so the same code runs locally
(via the CLI) and inside a Databricks App (via the SDK / injected PGPASSWORD).
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

_RESOURCES = json.loads((Path(__file__).resolve().parent.parent / "config" / "resources.json").read_text())
HOST = os.environ.get("PGHOST", _RESOURCES["lakebase_host"])
PG_DB = os.environ.get("PGDATABASE", _RESOURCES["lakebase_pg_database"])
SCHEMA = os.environ.get("FEBAR_LAKEBASE_SCHEMA", _RESOURCES["lakebase_schema"])
ENDPOINT = _RESOURCES["lakebase_endpoint"]
PROFILE = os.environ.get("FEBAR_PROFILE", _RESOURCES.get("profile", "fevm"))

_conn: psycopg.Connection | None = None
_token_ts: float = 0.0


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #
def _get_user() -> str:
    if os.environ.get("PGUSER"):
        return os.environ["PGUSER"]
    if os.environ.get("DATABRICKS_CLIENT_ID"):  # app service principal
        return os.environ["DATABRICKS_CLIENT_ID"]
    out = subprocess.run(["databricks", "current-user", "me", "--profile", PROFILE],
                         capture_output=True, text=True)
    return json.loads(out.stdout)["userName"]


def _get_token() -> str:
    # 1) explicitly injected password (if the platform provides one)
    if os.environ.get("PGPASSWORD"):
        return os.environ["PGPASSWORD"]
    # 2) Databricks App / runtime: mint a Lakebase credential via the REST API
    #    (POST /api/2.0/postgres/credentials) using the SDK's authenticated client.
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        resp = w.api_client.do("POST", "/api/2.0/postgres/credentials",
                               body={"endpoint": ENDPOINT})
        if resp and resp.get("token"):
            return resp["token"]
    except Exception:
        pass
    # 3) local dev: the CLI
    out = subprocess.run(
        ["databricks", "postgres", "generate-database-credential", ENDPOINT,
         "--profile", PROFILE, "-o", "json"],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"token generation failed: {out.stderr}")
    return json.loads(out.stdout)["token"]


def _connect() -> psycopg.Connection:
    user = _get_user()
    token = _get_token()
    conn = psycopg.connect(
        host=HOST, dbname=PG_DB, user=user, password=token,
        sslmode="require", connect_timeout=30, autocommit=True, row_factory=dict_row,
    )
    conn.execute(f"SET search_path TO {SCHEMA}, public")
    return conn


def get_conn() -> psycopg.Connection:
    """Return a live connection, (re)connecting and refreshing the token as needed.

    Lakebase scales to zero and OAuth tokens expire after ~1h, so we reconnect on
    failure and refresh the token roughly every 45 minutes.
    """
    global _conn, _token_ts
    if _conn is not None and (time.time() - _token_ts) < 2700:
        try:
            _conn.execute("SELECT 1")
            return _conn
        except Exception:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None
    _conn = _connect()
    _token_ts = time.time()
    return _conn


def q(sql: str, params: tuple = (), fetch: bool = False):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
    return None


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
def init_schema():
    ddl = (Path(__file__).resolve().parent / "create_tables.sql").read_text()
    conn = get_conn()
    # psycopg can execute a multi-statement script in one call
    conn.execute(ddl)


# --------------------------------------------------------------------------- #
# Persistence operations
# --------------------------------------------------------------------------- #
def persist_result(result: dict[str, Any]) -> None:
    """Insert/replace an enrichment result. Idempotent per transaction_id.
    AMBIGUOUS results are also enqueued for manual review (de-duplicated)."""
    txn = result.get("transaction_id")
    row = (
        txn, result["raw_descriptor"], result["descriptor_fingerprint"],
        Jsonb(result.get("extracted_entities")), result.get("merchant_id"),
        result.get("merchant_name"), result["decision"], result.get("confidence"),
        result.get("reason"), result.get("source"),
        Jsonb(result.get("candidates") or []),
    )
    # duplicate submission handling: if a result for this txn exists, replace it
    if txn:
        q("DELETE FROM merchant_enrichment_results WHERE transaction_id = %s", (txn,))
    q("""INSERT INTO merchant_enrichment_results
         (transaction_id, raw_descriptor, descriptor_fingerprint, extracted_entities,
          merchant_id, merchant_name, decision, confidence, reason, source, candidates)
         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", row)

    if result["decision"] == "AMBIGUOUS":
        enqueue_review(result)


def lookup_mapping(fingerprint: str) -> dict | None:
    rows = q("""SELECT merchant_id, merchant_name, confidence
                FROM merchant_mapping
                WHERE descriptor_fingerprint = %s AND mapping_status = 'CONFIRMED'""",
             (fingerprint,), fetch=True)
    return rows[0] if rows else None


def save_confirmed_mapping(fingerprint: str, merchant_id: str, merchant_name: str | None,
                           confidence: float | None) -> None:
    """Upsert a CONFIRMED mapping. Only confirmed mappings are ever stored here."""
    q("""INSERT INTO merchant_mapping
            (descriptor_fingerprint, merchant_id, merchant_name, confidence, mapping_status)
         VALUES (%s,%s,%s,%s,'CONFIRMED')
         ON CONFLICT (descriptor_fingerprint)
         DO UPDATE SET merchant_id = EXCLUDED.merchant_id,
                       merchant_name = EXCLUDED.merchant_name,
                       confidence = EXCLUDED.confidence,
                       confirmed_timestamp = now()""",
      (fingerprint, merchant_id, merchant_name, confidence))


def enqueue_review(result: dict[str, Any]) -> None:
    fp = result["descriptor_fingerprint"]
    existing = q("""SELECT review_id FROM manual_review_queue
                    WHERE descriptor_fingerprint = %s AND review_status = 'PENDING'""",
                 (fp,), fetch=True)
    if existing:
        return  # de-duplicate pending reviews
    q("""INSERT INTO manual_review_queue
            (transaction_id, raw_descriptor, descriptor_fingerprint, extracted_entities,
             candidate_merchants)
         VALUES (%s,%s,%s,%s,%s)""",
      (result.get("transaction_id"), result["raw_descriptor"], fp,
       Jsonb(result.get("extracted_entities")), Jsonb(result.get("candidates") or [])))


def list_review_queue(status: str = "PENDING", limit: int = 100) -> list[dict]:
    return q("""SELECT review_id, transaction_id, raw_descriptor, descriptor_fingerprint,
                       extracted_entities, candidate_merchants, review_status, created_timestamp
                FROM manual_review_queue WHERE review_status = %s
                ORDER BY created_timestamp DESC LIMIT %s""", (status, limit), fetch=True) or []


def approve_review(review_id: int, merchant_id: str, analyst: str = "analyst") -> dict:
    rows = q("SELECT * FROM manual_review_queue WHERE review_id = %s", (review_id,), fetch=True)
    if not rows:
        raise ValueError(f"review {review_id} not found")
    r = rows[0]
    fp = r["descriptor_fingerprint"]
    # resolve merchant_name from candidates
    merchant_name = None
    for c in (r.get("candidate_merchants") or []):
        if str(c.get("merchant_id")) == str(merchant_id):
            merchant_name = c.get("merchant_name")
    q("UPDATE manual_review_queue SET review_status = 'APPROVED' WHERE review_id = %s", (review_id,))
    save_confirmed_mapping(fp, merchant_id, merchant_name, 1.0)
    q("""INSERT INTO analyst_feedback
            (transaction_id, review_id, descriptor_fingerprint, selected_merchant_id,
             analyst_decision, analyst)
         VALUES (%s,%s,%s,%s,'APPROVED',%s)""",
      (r.get("transaction_id"), review_id, fp, merchant_id, analyst))
    # reflect the confirmed decision back onto the enrichment result
    q("""UPDATE merchant_enrichment_results
         SET decision='MATCHED', merchant_id=%s, merchant_name=%s, confidence=1.0,
             source='analyst_confirmed', reason='Confirmed by analyst via manual review.'
         WHERE descriptor_fingerprint=%s""", (merchant_id, merchant_name, fp))
    return {"review_id": review_id, "merchant_id": merchant_id, "merchant_name": merchant_name,
            "status": "APPROVED"}


def reject_review(review_id: int, analyst: str = "analyst") -> dict:
    rows = q("SELECT * FROM manual_review_queue WHERE review_id = %s", (review_id,), fetch=True)
    if not rows:
        raise ValueError(f"review {review_id} not found")
    r = rows[0]
    q("UPDATE manual_review_queue SET review_status = 'REJECTED' WHERE review_id = %s", (review_id,))
    q("""INSERT INTO analyst_feedback
            (transaction_id, review_id, descriptor_fingerprint, selected_merchant_id,
             analyst_decision, analyst)
         VALUES (%s,%s,%s,NULL,'REJECTED',%s)""",
      (r.get("transaction_id"), review_id, r["descriptor_fingerprint"], analyst))
    return {"review_id": review_id, "status": "REJECTED"}


# --------------------------------------------------------------------------- #
# Dashboard metrics (never hard-coded — always live from Postgres)
# --------------------------------------------------------------------------- #
def dashboard_metrics() -> dict[str, Any]:
    total = q("SELECT count(*) AS n FROM merchant_enrichment_results", fetch=True)[0]["n"]
    by_dec = {r["decision"]: r["n"] for r in
              q("SELECT decision, count(*) AS n FROM merchant_enrichment_results GROUP BY decision",
                fetch=True)}
    reuse = q("SELECT count(*) AS n FROM merchant_enrichment_results WHERE source='mapping_reuse'",
              fetch=True)[0]["n"]
    pending = q("SELECT count(*) AS n FROM manual_review_queue WHERE review_status='PENDING'",
                fetch=True)[0]["n"]
    confirmed = q("SELECT count(*) AS n FROM merchant_mapping", fetch=True)[0]["n"]
    matched = by_dec.get("MATCHED", 0)
    return {
        "total_processed": total,
        "matched": matched,
        "no_match": by_dec.get("NO_MATCH", 0),
        "ambiguous": by_dec.get("AMBIGUOUS", 0),
        "enrichment_success_rate": round(100 * matched / total, 1) if total else 0.0,
        "manual_review_pending": pending,
        "mapping_reuse_count": reuse,
        "confirmed_mappings": confirmed,
    }


def recent_activity(limit: int = 10) -> list[dict]:
    return q("""SELECT transaction_id, raw_descriptor, decision, merchant_name, confidence,
                       source, processed_timestamp
                FROM merchant_enrichment_results
                ORDER BY processed_timestamp DESC LIMIT %s""", (limit,), fetch=True) or []


if __name__ == "__main__":
    init_schema()
    print("schema initialized; metrics:", json.dumps(dashboard_metrics(), default=str))
