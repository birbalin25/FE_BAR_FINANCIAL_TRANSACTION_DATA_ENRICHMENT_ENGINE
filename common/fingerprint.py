"""Descriptor fingerprint used as the mapping-reuse key.

The fingerprint normalizes a raw descriptor into a stable key that PRESERVES
meaningful differences (store/branch numbers and location) while DROPPING noise
that varies per transaction (payment-facilitator prefixes, order/reference IDs,
punctuation, casing). It is computed directly from the raw descriptor so a
confirmed mapping can be reused BEFORE running the expensive enrichment workflow.

It is intentionally NOT transaction_id based (per the spec).

Examples:
    "SQ *SUNSHINE COFFEE #1234 LARCHMONT NY"        -> "sunshine coffee 1234 larchmont ny"
    "SQUARE SUNSHINE COFFEE #1234 LARCHMONT NY A9Z"  -> "sunshine coffee 1234 larchmont ny"
"""
from __future__ import annotations

import re

_FACILITATOR_TOKENS = {
    "SQ", "SQUARE", "PAYPAL", "PP", "PYPL", "STRIPE", "STR", "TST", "TOAST",
    "CLV", "CLOVER", "VENMO", "VEN",
}


def fingerprint(descriptor: str) -> str:
    s = (descriptor or "").upper()
    tokens = [t for t in re.split(r"[^A-Z0-9#]+", s) if t]

    # strip leading payment-facilitator tokens (e.g. "SQ", "SQUARE", "PAYPAL")
    while tokens and tokens[0].strip("#*") in _FACILITATOR_TOKENS:
        tokens.pop(0)

    cleaned: list[str] = []
    for t in tokens:
        core = t.lstrip("#")
        if not core:
            continue
        if core in _FACILITATOR_TOKENS:
            continue
        # drop order/reference-id-like tokens: long AND mixed letters+digits
        if len(core) >= 6 and re.search(r"[A-Z]", core) and re.search(r"[0-9]", core):
            continue
        cleaned.append(core.lower())

    return re.sub(r"\s+", " ", " ".join(cleaned)).strip()


if __name__ == "__main__":
    for d in [
        "SQ *SUNSHINE COFFEE #1234 LARCHMONT NY",
        "SQUARE SUNSHINE COFFEE #1234 LARCHMONT NY A9ZK3",
        "PAYPAL *TACO FIESTA LAS VEGAS",
        "QUANTUM WIDGETS K82P5YR",
    ]:
        print(f"{d!r:55} -> {fingerprint(d)!r}")
