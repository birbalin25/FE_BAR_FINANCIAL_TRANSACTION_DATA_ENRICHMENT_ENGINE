"""Thin local orchestration helpers for Databricks, built on the `databricks` CLI.

Why the CLI and not the SDK?  This project is driven from a workstation that can
only reach allow-listed Databricks hosts (no PyPI), so we avoid extra Python
dependencies locally and shell out to the already-installed `databricks` CLI.
Heavy compute (Spark, Vector Search indexing, MLflow) runs *inside* Databricks.

Primary entry points:
    run_sql(statement, ...)   -> execute SQL via the Statement Execution API
    rows(statement, ...)      -> list[dict] convenience wrapper
    scalar(statement, ...)    -> single value
    workspace_token()         -> OAuth token (for FMAPI via the openai client)

All functions accept an optional `profile` (defaults to the configured one).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any

from common.config import CFG


def _cli_available() -> bool:
    return shutil.which("databricks") is not None


class DbxError(RuntimeError):
    pass


def _cli(args: list[str], profile: str | None = None, input_json: str | None = None) -> str:
    profile = profile or CFG.profile
    cmd = ["databricks", *args, "--profile", profile]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          input=input_json if input_json is not None else None)
    if proc.returncode != 0:
        raise DbxError(f"CLI failed: {' '.join(cmd)}\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}")
    return proc.stdout


def _api(method: str, path: str, payload: dict | None = None, profile: str | None = None) -> dict:
    args = ["api", method, path]
    if payload is not None:
        args += ["--json", json.dumps(payload)]
    out = _cli(args, profile=profile)
    out = out.strip()
    return json.loads(out) if out else {}


def workspace_token(profile: str | None = None) -> str:
    """Return a short-lived OAuth access token for the workspace."""
    out = _cli(["auth", "token"], profile=profile)
    return json.loads(out)["access_token"]


def _run_sql_sdk(statement: str, warehouse_id: str, catalog: str | None,
                 schema: str | None) -> dict:
    """SDK-based execution for runtimes without the CLI (e.g. Databricks Apps)."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState
    w = WorkspaceClient()
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement,
        catalog=catalog, schema=schema, wait_timeout="50s",
    )
    # poll if needed
    while resp.status and resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        raise DbxError(f"SQL {resp.status.state}: "
                       f"{resp.status.error.message if resp.status.error else resp}")
    cols = [c.name for c in resp.manifest.schema.columns] if resp.manifest and resp.manifest.schema else []
    data = (resp.result.data_array if resp.result else None) or []
    return {"manifest": {"schema": {"columns": [{"name": c} for c in cols]}},
            "result": {"data_array": data}, "status": {"state": "SUCCEEDED"}}


def run_sql(statement: str, *, warehouse_id: str | None = None, catalog: str | None = None,
            schema: str | None = None, profile: str | None = None,
            wait: str = "50s", poll_timeout_s: int = 600) -> dict:
    """Execute a SQL statement and return the full API response (polling if needed)."""
    warehouse_id = warehouse_id or CFG.databricks["warehouse_id"]
    if not _cli_available():
        return _run_sql_sdk(statement, warehouse_id, catalog, schema)
    payload: dict[str, Any] = {
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": wait,
        "format": "JSON_ARRAY",
        "disposition": "INLINE",
    }
    if catalog:
        payload["catalog"] = catalog
    if schema:
        payload["schema"] = schema
    resp = _api("post", "/api/2.0/sql/statements/", payload, profile=profile)

    stmt_id = resp.get("statement_id")
    deadline = time.time() + poll_timeout_s
    while resp.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() > deadline:
            raise DbxError(f"SQL polling timed out for statement {stmt_id}")
        time.sleep(2)
        resp = _api("get", f"/api/2.0/sql/statements/{stmt_id}", profile=profile)

    state = resp.get("status", {}).get("state")
    if state != "SUCCEEDED":
        err = resp.get("status", {}).get("error", {})
        raise DbxError(f"SQL {state}: {err.get('message', resp)}\n--SQL--\n{statement[:1500]}")
    return resp


def _columns(resp: dict) -> list[str]:
    return [c["name"] for c in resp.get("manifest", {}).get("schema", {}).get("columns", [])]


def rows(statement: str, **kw) -> list[dict]:
    """Execute SQL and return results as a list of dicts (column name -> value)."""
    resp = run_sql(statement, **kw)
    cols = _columns(resp)
    data = resp.get("result", {}).get("data_array") or []
    return [dict(zip(cols, r)) for r in data]


def scalar(statement: str, **kw):
    r = rows(statement, **kw)
    if not r:
        return None
    return next(iter(r[0].values()))


def exec_many(statements: list[str], **kw) -> None:
    """Execute a list of statements sequentially (DDL etc.)."""
    for s in statements:
        s = s.strip().rstrip(";")
        if s:
            run_sql(s, **kw)
