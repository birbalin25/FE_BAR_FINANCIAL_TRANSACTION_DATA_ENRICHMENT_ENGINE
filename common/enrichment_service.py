"""End-to-end merchant enrichment orchestrator.

Ties together the full workflow for a single transaction descriptor:

    1. (optional) mapping-reuse check in Lakebase by descriptor fingerprint
    2. GenAI entity recognition
    3. Vector Search top-10 candidate retrieval
    4. LLM judge -> MATCHED / NO_MATCH / AMBIGUOUS
    5. (optional) persistence to Lakebase

Lakebase access is injected via callables (`reuse_lookup`, `persist`) so this
module has no hard dependency on Postgres and is equally usable from batch
evidence scripts, the evaluation harness, and the Databricks App.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from common.config import CFG
from common.fingerprint import fingerprint
from entity_recognition.entity_extraction import extract_entities, query_text
from entity_linkage.llm_judge import judge
from vector_search.retrieve_candidates import retrieve_candidates

# Confidence thresholds (calibrated against evaluation data in Phase 6).
MATCH_CONFIDENCE_THRESHOLD = 0.70


def enrich(
    descriptor: str,
    *,
    transaction_id: str | None = None,
    reuse_lookup: Callable[[str], dict | None] | None = None,
    persist: Callable[[dict], None] | None = None,
    model: str | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Run the enrichment workflow for one descriptor and return a rich result dict."""
    t0 = time.time()
    fp = fingerprint(descriptor)
    result: dict[str, Any] = {
        "transaction_id": transaction_id,
        "raw_descriptor": descriptor,
        "descriptor_fingerprint": fp,
        "source": None,                 # "mapping_reuse" | "enrichment_workflow"
        "extracted_entities": None,
        "candidates": [],
        "decision": None,
        "merchant_id": None,
        "merchant_name": None,
        "confidence": None,
        "reason": None,
        "alternative_candidates": [],
        "llm_calls": 0,
        "processed_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # --- 1. Mapping reuse: skip the whole workflow on a confirmed hit ---------
    if reuse_lookup is not None:
        hit = reuse_lookup(fp)
        if hit:
            result.update({
                "source": "mapping_reuse",
                "decision": "MATCHED",
                "merchant_id": hit.get("merchant_id"),
                "merchant_name": hit.get("merchant_name"),
                "confidence": hit.get("confidence", 1.0),
                "reason": "Reused a previously confirmed merchant mapping (fingerprint match).",
                "latency_ms": int((time.time() - t0) * 1000),
            })
            if persist is not None:
                persist(result)
            return result

    # --- 2. Entity recognition -----------------------------------------------
    entities = extract_entities(descriptor, model=model)
    result["extracted_entities"] = entities
    result["llm_calls"] += 1

    # --- 3. Vector Search candidate retrieval --------------------------------
    q = query_text(entities) or descriptor
    candidates = retrieve_candidates(q, top_k=top_k)
    result["candidates"] = candidates

    # --- 4. LLM judge ---------------------------------------------------------
    decision = judge(descriptor, entities, candidates, model=model)
    result["llm_calls"] += 1
    result.update({
        "source": "enrichment_workflow",
        "decision": decision["decision"],
        "merchant_id": decision["merchant_id"],
        "merchant_name": decision["merchant_name"],
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "alternative_candidates": decision["alternative_candidates"],
    })

    # Threshold guardrail: a weak MATCHED is downgraded to AMBIGUOUS (manual review).
    if result["decision"] == "MATCHED" and (result["confidence"] or 0) < MATCH_CONFIDENCE_THRESHOLD:
        result["decision"] = "AMBIGUOUS"
        result["reason"] = (f"Confidence {result['confidence']} below threshold "
                            f"{MATCH_CONFIDENCE_THRESHOLD}; routed to manual review. "
                            + (result["reason"] or ""))
        result["merchant_id"] = None
        result["merchant_name"] = None

    result["latency_ms"] = int((time.time() - t0) * 1000)

    # --- 5. Persist -----------------------------------------------------------
    if persist is not None:
        persist(result)
    return result


if __name__ == "__main__":
    import json
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY"
    print(json.dumps(enrich(d), indent=2, default=str))
