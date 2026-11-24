"""LLM entity-linkage judge.

Given the original descriptor, the extracted entities, and the top-K Vector
Search candidates, an LLM decides MATCHED / NO_MATCH / AMBIGUOUS and explains
why. It must never force a match, never invent a merchant, and must weigh name
AND location together. The selected merchant_id must come from the candidate set.

Output schema (validated):
    {
      "decision": "MATCHED" | "NO_MATCH" | "AMBIGUOUS",
      "merchant_id": <id from candidates or null>,
      "merchant_name": <name or null>,
      "confidence": <float 0..1>,
      "reason": <str>,
      "alternative_candidates": [<merchant_id>, ...]
    }
"""
from __future__ import annotations

import json
from typing import Any

from common.llm import chat_json

VALID_DECISIONS = {"MATCHED", "NO_MATCH", "AMBIGUOUS"}

SYSTEM_PROMPT = """You are a meticulous merchant entity-linkage judge for a retail bank. \
You decide whether a noisy card-transaction descriptor can be reliably linked to exactly \
one canonical merchant from a shortlist of candidates retrieved by vector search.

You are given: the original descriptor, the entities already extracted from it, and a \
numbered list of candidate merchants (each with merchant_id, name, city, state, category, \
and a vector similarity_score).

Decide ONE of:
- MATCHED: exactly one candidate is a reliable match. Name AND location are consistent with \
the descriptor. Pick that candidate's merchant_id.
- AMBIGUOUS: two or more candidates are plausible and cannot be separated with the available \
information (e.g. the descriptor names a chain but has no location, so multiple branches fit). \
Additional investigation is required. Do NOT pick a single merchant_id (use null).
- NO_MATCH: none of the candidates can be reliably linked to the descriptor.

Hard rules:
- NEVER force a match. A high similarity_score alone is NOT sufficient evidence.
- Evaluate merchant name AND location TOGETHER. If the descriptor has a city/state, the \
chosen merchant's city/state must be consistent.
- DECISIVE LOCATION RULE: when the descriptor contains a location (city and/or state) and \
EXACTLY ONE candidate's name is consistent with the descriptor AND its city/state matches that \
location, choose MATCHED for that candidate. The existence of other same-name candidates in \
DIFFERENT cities/states does NOT make it ambiguous — the location disambiguates them. (e.g. \
descriptor 'PRECISION AUTO PARTS MIAMI' with candidates in Miami, Dallas, and Boston -> MATCHED \
to the Miami one.)
- AMBIGUOUS applies ONLY when you genuinely cannot separate candidates: the descriptor gives no \
usable location AND multiple candidates share the name, OR two or more candidates match the SAME \
location so you cannot pick one.
- Treat missing information as UNKNOWN, never as positive evidence.
- The chosen merchant_id MUST be one of the candidate merchant_ids. NEVER invent an id or \
attributes not present in the candidate list.
- Provide a short, concrete reason for every decision.
- confidence is your calibrated probability (0..1) that the decision is correct.
- alternative_candidates: up to 3 other plausible candidate merchant_ids (for MATCHED/AMBIGUOUS)."""


def _format_candidates(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"{i}. merchant_id={c.get('merchant_id')} | name={c.get('merchant_name')} | "
            f"city={c.get('city')} | state={c.get('state')} | "
            f"category={c.get('merchant_category')} | similarity={c.get('similarity_score')}"
        )
    return "\n".join(lines) if lines else "(no candidates)"


def judge(descriptor: str, entities: dict, candidates: list[dict], *,
          model: str | None = None) -> dict[str, Any]:
    """Adjudicate the match. Always returns a valid, schema-conformant dict."""
    candidate_ids = {str(c.get("merchant_id")) for c in candidates}

    if not candidates:
        return {"decision": "NO_MATCH", "merchant_id": None, "merchant_name": None,
                "confidence": 0.0, "reason": "No candidate merchants were retrieved.",
                "alternative_candidates": []}

    user = (
        f'Original descriptor: "{descriptor}"\n\n'
        f"Extracted entities: {json.dumps(entities)}\n\n"
        f"Candidate merchants (top {len(candidates)} by vector similarity):\n"
        f"{_format_candidates(candidates)}\n\n"
        "Return the decision JSON."
    )

    try:
        raw = chat_json(SYSTEM_PROMPT, user, model=model, max_tokens=600)
    except Exception as e:  # noqa: BLE001
        return {"decision": "AMBIGUOUS", "merchant_id": None, "merchant_name": None,
                "confidence": 0.0, "reason": f"Judge error, routed to review: {e}",
                "alternative_candidates": []}

    return _validate(raw, candidates, candidate_ids)


def _validate(raw: dict, candidates: list[dict], candidate_ids: set[str]) -> dict[str, Any]:
    decision = str(raw.get("decision", "")).upper().strip()
    if decision not in VALID_DECISIONS:
        decision = "AMBIGUOUS"

    merchant_id = raw.get("merchant_id")
    merchant_id = str(merchant_id) if merchant_id not in (None, "", "null") else None

    # Guardrail: a chosen merchant_id MUST come from the candidate set.
    if merchant_id and merchant_id not in candidate_ids:
        merchant_id = None
        if decision == "MATCHED":
            decision = "AMBIGUOUS"

    # MATCHED requires a concrete merchant_id.
    if decision == "MATCHED" and not merchant_id:
        decision = "AMBIGUOUS"
    # NO_MATCH / AMBIGUOUS must not carry a single merchant_id.
    if decision in ("NO_MATCH", "AMBIGUOUS"):
        merchant_id = None

    # resolve merchant_name from the chosen candidate (never trust the LLM's copy)
    merchant_name = None
    if merchant_id:
        for c in candidates:
            if str(c.get("merchant_id")) == merchant_id:
                merchant_name = c.get("merchant_name")
                break

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    alts = raw.get("alternative_candidates") or []
    if isinstance(alts, str):
        alts = [alts]
    alts = [str(a) for a in alts if str(a) in candidate_ids and str(a) != merchant_id][:3]

    reason = str(raw.get("reason", "")).strip() or "No reason provided."

    return {"decision": decision, "merchant_id": merchant_id, "merchant_name": merchant_name,
            "confidence": round(confidence, 3), "reason": reason,
            "alternative_candidates": alts}
