# Genie Space — Business Definitions & Instructions

This document is the human-readable version of the instructions configured on the
**"Merchant Enrichment Analytics"** Genie space (configured programmatically by
[`create_genie_space.py`](create_genie_space.py)). The space answers natural-language
questions for the Payments Operations team over three governed Unity Catalog Gold tables.

## What "merchant enrichment" means

Merchant enrichment is the process of turning a messy, unstructured card-transaction
descriptor (e.g. `SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY`) into a standardized,
identified merchant. Every processed transaction receives exactly one **decision**.

## Decision definitions

| Decision | Meaning |
|---|---|
| **MATCHED** | The transaction was reliably linked to exactly one canonical merchant. |
| **NO_MATCH** | No candidate merchant could be reliably linked to the descriptor. |
| **AMBIGUOUS** | Multiple merchants are plausible; the transaction is routed to analyst **manual review**. |

## Metric definitions (consistent with the data)

- **Enrichment success rate** = `count(decision='MATCHED') / count(*)` over `gold_enrichment_results` (as a %).
- **Unmatched rate** = `count(decision='NO_MATCH') / count(*)`.
- **Manual review rate** = `count(decision='AMBIGUOUS') / count(*)`. Transactions *awaiting manual review* are the AMBIGUOUS ones.
- **Matching precision** = of MATCHED decisions, the % that are correct (from `gold_enrichment_quality_metrics`, measured on held-out ground truth).
- **Matching recall** = of truly-matchable transactions, the % the system correctly matched.
- **Recall@10** = % of matchable transactions whose correct merchant was in the Vector Search top-10 candidates.
- **False-positive rate** = % of MATCHED decisions that are incorrect — the key risk metric.

## Payment facilitator vs merchant

The **payment facilitator** (Square, PayPal, Stripe, Toast, Clover, Venmo) is the payment
processor that routed the transaction — it is **not** the merchant. The merchant is the actual
business (identified by `merchant_id` / `merchant_name`). A descriptor like `SQ *SUNSHINE COFFEE`
has facilitator = Square and merchant = Sunshine Coffee.

## Which table answers which question

| Table | Use for |
|---|---|
| `gold_enrichment_results` | Decision counts & rates, unmatched/ambiguous %, facilitators, categories, time trends. |
| `gold_merchant_metrics` | Per-merchant transaction volumes ("highest-volume merchants"). |
| `gold_enrichment_quality_metrics` | Model accuracy: precision, recall, Recall@10, false-positive rate. |

## Relationships / joins

- `gold_enrichment_results.merchant_id` → `gold_merchant_metrics.merchant_id` → `gold_merchants.merchant_id`.
- Time trends use `gold_enrichment_results.processed_timestamp`.
