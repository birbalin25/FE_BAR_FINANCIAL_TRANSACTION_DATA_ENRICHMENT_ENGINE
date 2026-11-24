"""Operational enrichment entry point used by the Databricks App and demos.

Wraps the pure `enrich()` workflow with Lakebase persistence and mapping reuse:
  * checks Lakebase for a confirmed mapping first (fingerprint key)
  * persists every result
  * auto-confirms high-confidence MATCHED results so equivalent future
    descriptors reuse the mapping (analyst approvals also create confirmed
    mappings, via lakebase.persistence.approve_review)
"""
from __future__ import annotations

from typing import Any

from common.enrichment_service import enrich
from lakebase import persistence as lb

# A fresh MATCHED result at/above this confidence becomes a reusable confirmed mapping.
AUTO_CONFIRM_THRESHOLD = 0.90


def enrich_and_persist(descriptor: str, *, transaction_id: str | None = None) -> dict[str, Any]:
    result = enrich(
        descriptor,
        transaction_id=transaction_id,
        reuse_lookup=lb.lookup_mapping,
        persist=lb.persist_result,
    )
    # auto-confirm strong fresh matches for future reuse
    if (result.get("source") == "enrichment_workflow"
            and result.get("decision") == "MATCHED"
            and result.get("merchant_id")
            and (result.get("confidence") or 0) >= AUTO_CONFIRM_THRESHOLD):
        lb.save_confirmed_mapping(
            result["descriptor_fingerprint"], result["merchant_id"],
            result.get("merchant_name"), result.get("confidence"),
        )
    return result
