"""Retrieve top-K merchant candidates from Databricks Vector Search.

Queries the managed-embedding Delta Sync index with a text query built from the
LLM-extracted merchant entities (the index embeds the query with
`databricks-gte-large-en`). Returns candidate merchant records with a similarity
score, which the LLM judge then adjudicates.

Uses the REST query endpoint via the CLI `databricks api` passthrough (the typed
CLI `query-index` has a response-unmarshalling bug; the raw REST call is clean)
so it needs no extra Python dependencies locally. Inside Databricks Apps the same
REST path works with the runtime token.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from common.config import CFG

INDEX = CFG.vector_search["index_name"]
TOP_K = CFG.vector_search["top_k"]
RETURN_COLUMNS = ["merchant_id", "merchant_name", "address", "city", "state",
                  "country", "postal_code", "merchant_category"]


def _query_rest(body: dict) -> dict:
    """POST to the VS query endpoint.

    Local dev → the `databricks` CLI passthrough (reliable auth + TLS). App
    runtime (no CLI) → direct HTTPS with the injected/runtime token.
    """
    path = f"/api/2.0/vector-search/indexes/{INDEX}/query"
    if shutil.which("databricks"):
        cmd = ["databricks", "api", "post", path, "--profile", CFG.profile,
               "--json", json.dumps(body)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return json.loads(p.stdout)
        # fall through to HTTP on CLI failure
    import urllib.request
    token = os.environ.get("DATABRICKS_TOKEN")
    if not token:
        try:  # Databricks App / runtime service principal
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            token = w.config.oauth_token().access_token
        except Exception:
            from common.dbx import workspace_token
            token = workspace_token()
    ctx = None
    try:
        import ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = None
    base = os.environ.get("DATABRICKS_HOST", CFG.host).rstrip("/")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:  # noqa: S310
        return json.loads(r.read())


def retrieve_candidates(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    """Return up to top_k candidate merchant dicts, each with a similarity_score."""
    query = (query or "").strip()
    if not query:
        return []
    top_k = top_k or TOP_K
    body = {"columns": RETURN_COLUMNS, "query_text": query, "num_results": top_k}
    resp = _query_rest(body)
    cols = [c["name"] for c in resp.get("manifest", {}).get("columns", [])]
    out = []
    for row in resp.get("result", {}).get("data_array", []) or []:
        rec = dict(zip(cols, row))
        # the trailing column is the similarity score
        rec["similarity_score"] = round(float(rec.pop("score", row[-1])), 4)
        out.append(rec)
    return out


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "Sunshine Coffee Roasters Larchmont NY"
    for c in retrieve_candidates(q):
        print(f"{c['similarity_score']:.3f}  {c['merchant_id']}  {c['merchant_name']}  "
              f"{c['city']}, {c['state']}  ({c['merchant_category']})")
