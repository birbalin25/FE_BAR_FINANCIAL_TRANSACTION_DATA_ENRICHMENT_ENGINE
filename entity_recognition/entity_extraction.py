"""GenAI merchant entity recognition.

Given a raw, unstructured transaction descriptor, an LLM extracts the structured
entities that identify the merchant, distinguishing the payment facilitator from
the actual merchant, the location, the store identifier, and any order/transaction
identifier or irrelevant tokens.

The response is validated against a fixed schema; missing or malformed responses
are handled gracefully (every field defaults to None).

Example:
    >>> extract_entities("SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY")
    {'payment_facilitator': 'Square', 'merchant_name': 'Sunshine Coffee Roasters',
     'city': 'Larchmont', 'state': 'NY', 'country': 'USA', 'store_identifier': None,
     'order_identifier': None}
"""
from __future__ import annotations

from typing import Any

from common.llm import chat_json

# Fixed output schema: field -> expected python type
SCHEMA: dict[str, type] = {
    "payment_facilitator": str,
    "merchant_name": str,
    "city": str,
    "state": str,
    "country": str,
    "store_identifier": str,
    "order_identifier": str,
}

SYSTEM_PROMPT = """You are a payments-data specialist that parses raw card-transaction \
descriptors into structured merchant entities for a retail bank.

A raw descriptor is noisy: it may contain a payment-facilitator prefix (e.g. "SQ *", \
"SQUARE", "PAYPAL *", "PP*", "STRIPE", "TST*" for Toast, "CLV*" for Clover, "VENMO *"), \
the actual merchant/business name (often abbreviated, misspelled, or truncated), a \
location (city/state), a store or branch identifier (e.g. "#1234", "STORE 42", "ST#07"), \
an order/transaction identifier (random-looking alphanumeric tokens), and irrelevant noise.

Extract these fields and return them as JSON:
- payment_facilitator: the payment processor/facilitator brand ONLY if present \
(e.g. "Square", "PayPal", "Stripe", "Toast", "Clover", "Venmo"). This is NOT the merchant. \
Null if none.
- merchant_name: the actual business/merchant name, de-abbreviated to your best guess of \
the real name, WITHOUT the facilitator prefix, store number, or location.
- city: the city if present, else null.
- state: the 2-letter US state code if present, else null.
- country: the country (use "USA" for US transactions) if inferable, else null.
- store_identifier: the store/branch number or code if present (keep it, e.g. "1234"), else null.
- order_identifier: any order/transaction/reference id that is clearly not a store number, else null.

Rules:
- Separate the facilitator from the merchant. "SQ *SUNSHINE COFFEE" -> facilitator "Square", merchant "Sunshine Coffee".
- Do not invent a location or store number that is not in the descriptor. Use null for anything absent.
- If the descriptor contains no recognizable merchant, set merchant_name to null.
- Keep merchant_name concise and human-readable (title case)."""


def _validate(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce the LLM output to the fixed schema; unknown/missing -> None."""
    out: dict[str, Any] = {}
    for field in SCHEMA:
        val = raw.get(field)
        if val is None:
            out[field] = None
            continue
        s = str(val).strip()
        if s == "" or s.lower() in ("null", "none", "n/a", "unknown"):
            out[field] = None
        else:
            out[field] = s
    # normalize country
    if out.get("country") and out["country"].upper() in ("US", "U.S.", "U.S.A", "USA", "UNITED STATES"):
        out["country"] = "USA"
    # normalize state to upper
    if out.get("state"):
        out["state"] = out["state"].upper()[:2] if len(out["state"]) <= 3 else out["state"]
    return out


def extract_entities(descriptor: str, *, model: str | None = None) -> dict[str, Any]:
    """Extract structured merchant entities from a raw descriptor.

    Always returns a dict with every SCHEMA key (None on failure/absence).
    """
    descriptor = (descriptor or "").strip()
    if not descriptor:
        return {k: None for k in SCHEMA}
    try:
        raw = chat_json(SYSTEM_PROMPT, f'Descriptor: "{descriptor}"', model=model, max_tokens=400)
        return _validate(raw if isinstance(raw, dict) else {})
    except Exception:
        # graceful degradation: empty extraction
        return {k: None for k in SCHEMA}


def query_text(entities: dict[str, Any]) -> str:
    """Build a Vector Search query string from extracted entities."""
    parts = [entities.get("merchant_name") or ""]
    loc = " ".join(p for p in (entities.get("city"), entities.get("state")) if p)
    if loc:
        parts.append(loc)
    return " ".join(p for p in parts if p).strip()


if __name__ == "__main__":
    import json
    import sys
    demo = sys.argv[1] if len(sys.argv) > 1 else "SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY"
    print(json.dumps(extract_entities(demo), indent=2))
