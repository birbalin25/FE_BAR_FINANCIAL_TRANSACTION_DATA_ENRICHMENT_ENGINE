"""Execute real natural-language questions against the configured Genie space via
the Genie Conversation API, and capture the generated SQL + actual query results
into genie/evidence/genie_query_results.md.

Run:  PYTHONPATH=. python3 genie/run_genie_queries.py
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from common.config import CFG
from common.evidence import header, md_table, code_block

RP = Path(__file__).resolve().parent.parent / "config" / "resources.json"
RES = json.loads(RP.read_text())
SPACE_ID = RES.get("genie_space_id")

QUESTIONS = [
    "How many transactions have been successfully enriched?",
    "What percentage of transactions remain unmatched?",
    "Which payment facilitators generate the most ambiguous transactions?",
    "What is the overall merchant enrichment success rate?",
    "Which merchants have the highest transaction volumes?",
]


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    args = ["databricks", "api", method, path, "--profile", CFG.profile]
    if payload is not None:
        args += ["--json", json.dumps(payload)]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{method} {path} failed: {p.stderr}\n{p.stdout}")
    return json.loads(p.stdout) if p.stdout.strip() else {}


def ask(question: str) -> dict:
    """Start a conversation, poll to completion, return message + any SQL/result."""
    start = _api("post", f"/api/2.0/genie/spaces/{SPACE_ID}/start-conversation",
                 {"content": question})
    conv_id = start.get("conversation_id") or start.get("conversation", {}).get("id")
    msg_id = start.get("message_id") or start.get("message", {}).get("id")

    msg = {}
    for _ in range(60):
        msg = _api("get", f"/api/2.0/genie/spaces/{SPACE_ID}/conversations/{conv_id}/messages/{msg_id}")
        status = msg.get("status")
        if status in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            break
        time.sleep(3)

    out = {"question": question, "status": msg.get("status"), "sql": None,
           "narrative": None, "columns": [], "rows": []}
    for att in msg.get("attachments", []) or []:
        if att.get("text"):
            out["narrative"] = att["text"].get("content")
        if att.get("query"):
            qy = att["query"]
            out["sql"] = qy.get("query")
            att_id = att.get("attachment_id")
            try:
                res = _api("get", f"/api/2.0/genie/spaces/{SPACE_ID}/conversations/{conv_id}"
                                  f"/messages/{msg_id}/attachments/{att_id}/query-result")
                sr = (res.get("statement_response") or {})
                cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                data = sr.get("result", {}).get("data_array") or []
                out["columns"] = cols
                out["rows"] = [dict(zip(cols, r)) for r in data]
            except Exception as e:  # noqa: BLE001
                out["result_error"] = str(e)[:200]
    return out


def main():
    if not SPACE_ID:
        raise SystemExit("No genie_space_id in resources.json — run create_genie_space.py first.")
    print(f"querying Genie space {SPACE_ID} ...")
    results = []
    for q in QUESTIONS:
        print(f"  Q: {q}")
        try:
            results.append(ask(q))
        except Exception as e:  # noqa: BLE001
            results.append({"question": q, "status": f"ERROR: {e}", "sql": None, "rows": []})
        time.sleep(1)

    ok = sum(1 for r in results if r.get("rows") or r.get("narrative"))
    parts = [header("Phase 4 Evidence — Genie Space Natural-Language Queries",
        f"Actual questions executed against the configured Genie space "
        f"`{SPACE_ID}` via the Genie Conversation API. {ok}/{len(results)} returned answers. "
        f"Space URL: {RES.get('genie_space_url')}")]
    for i, r in enumerate(results, 1):
        parts.append(f"\n---\n\n## Q{i}. {r['question']}\n")
        parts.append(f"**Status:** `{r.get('status')}`\n")
        if r.get("narrative"):
            parts.append(f"\n**Genie answer:** {r['narrative']}\n")
        if r.get("sql"):
            parts.append("\n**Generated SQL:**\n")
            parts.append(code_block(r["sql"], "sql"))
        if r.get("rows"):
            parts.append("\n**Query result:**\n")
            parts.append(md_table(r["rows"]))
        elif r.get("result_error"):
            parts.append(f"\n_(result fetch note: {r['result_error']})_\n")
    out = Path(__file__).resolve().parent / "evidence" / "genie_query_results.md"
    out.write_text("\n".join(parts))
    print(f"wrote {out} ({ok}/{len(results)} answered)")


if __name__ == "__main__":
    main()
