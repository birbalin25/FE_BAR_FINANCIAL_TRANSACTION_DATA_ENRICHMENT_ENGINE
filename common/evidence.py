"""Helpers to render live query results as readable Markdown evidence.

The FE Bar evaluator reads repository content as text, so every component writes
actual execution output into evidence/*.md via these helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone


def md_table(rows: list[dict], columns: list[str] | None = None, max_rows: int = 50,
             max_col_width: int = 80) -> str:
    """Render a list of row-dicts as a GitHub-flavored Markdown table."""
    if not rows:
        return "_(no rows)_\n"
    columns = columns or list(rows[0].keys())

    def cell(v):
        s = "" if v is None else str(v)
        s = s.replace("\n", " ").replace("|", "\\|")
        if len(s) > max_col_width:
            s = s[: max_col_width - 1] + "…"
        return s

    out = ["| " + " | ".join(columns) + " |",
           "| " + " | ".join("---" for _ in columns) + " |"]
    for r in rows[:max_rows]:
        out.append("| " + " | ".join(cell(r.get(c)) for c in columns) + " |")
    if len(rows) > max_rows:
        out.append(f"\n_… {len(rows) - max_rows} more rows omitted_")
    return "\n".join(out) + "\n"


def header(title: str, subtitle: str | None = None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    s = f"# {title}\n\n_Captured: {ts}_\n"
    if subtitle:
        s += f"\n{subtitle}\n"
    return s + "\n"


def code_block(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}\n```\n"
