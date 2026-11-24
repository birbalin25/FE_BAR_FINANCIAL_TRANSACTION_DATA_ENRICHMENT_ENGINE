# Phase 3 Evidence — Lakebase Operational Serving

_Captured: 2026-11-24 03:05:18 UTC_

Live reads/writes against the Lakebase (Autoscaling Postgres) project `febar-lakebase`, schema `febar_ops`. Demonstrates persistence, confirmed-mapping reuse, the manual-review queue, analyst feedback, and duplicate handling.



## 1. Fresh enrichment is persisted (source = enrichment_workflow)


### enrich_and_persist(descriptor) #1

```json
{
  "decision": "MATCHED",
  "merchant_id": "M00028",
  "merchant_name": "Sunshine Coffee Roasters",
  "confidence": 0.96,
  "source": "enrichment_workflow",
  "descriptor_fingerprint": "sunshine coffee roasters larchmont ny"
}
```


## 2. Confirmed mapping auto-saved for a strong match


### merchant_mapping row (by fingerprint)

```json
{
  "merchant_id": "M00028",
  "merchant_name": "Sunshine Coffee Roasters",
  "confidence": 0.96
}
```


## 3. Re-submitting the SAME descriptor reuses the mapping (skips extraction + Vector Search + judge)


### enrich_and_persist(descriptor) #2

```json
{
  "decision": "MATCHED",
  "merchant_id": "M00028",
  "merchant_name": "Sunshine Coffee Roasters",
  "confidence": 0.96,
  "source": "mapping_reuse",
  "latency_ms": 246
}
```


> Note the `source` is now **mapping_reuse** and latency dropped from **4131 ms** to **246 ms** (2 LLM calls → 0 LLM calls).


## 4. Duplicate submission handling (same transaction_id)


Resubmitting transaction `DEMO-002` keeps a single row (before=1, after=1) — the prior result is replaced, not duplicated.


## 5. An AMBIGUOUS descriptor is persisted and queued for manual review


### enrich_and_persist(ambiguous)

```json
{
  "decision": "AMBIGUOUS",
  "merchant_id": null,
  "confidence": 0.95,
  "source": "enrichment_workflow",
  "descriptor_fingerprint": "taco fiesta"
}
```


**Manual review queue (PENDING):**

| review_id | transaction_id | raw_descriptor | n_candidates | status |
| --- | --- | --- | --- | --- |
| 70 | DEMO-003 | PAYPAL *TACO FIESTA | 10 | PENDING |
| 69 | T007382 | QUICKFUEL AGS | 10 | PENDING |
| 68 | T007139 | COR MARKET - MONTGOMERY | 10 | PENDING |
| 67 | T006892 | STR*BLUE CAFE * AURORA | 10 | PENDING |
| 66 | T007236 | HAPPYPAWSPETSUPPL | 10 | PENDING |
| 65 | T006972 | TST*THE BURGER JOINT | 10 | PENDING |
| 64 | T006880 | URBANTREADS*LOC9880 | 10 | PENDING |
| 63 | T006970 | PIXELFORGE SUDIOS | 10 | PENDING |
| 62 | T006508 | PAYPAL *GREEN LEAF SALADS / LOC 0540 / BOULDER / IT0GDUFD3A | 10 | PENDING |
| 61 | T006764 | IRONW FITN | 10 | PENDING |
| 60 | T006598 | TST* THE BURGER - VPJGXKVAP | 10 | PENDING |
| 59 | T006469 | COY HOME GOODS  BX8P4JL6 | 10 | PENDING |
| 58 | T006321 | SQ*CLO MEDIA - AUSTIN | 10 | PENDING |
| 57 | T006454 | CITY DENTAL CARE  #1881 | 10 | PENDING |
| 56 | T006301 | STR*SUNSHINE COFFEE RO / STORE 4030 | 10 | PENDING |
| 55 | T006068 | PYPL *BELLA NAPOL PIZZERIA / LOC 1068 / CAMBRIDGE | 10 | PENDING |
| 54 | T005958 | BUILDERS DE  BALTIMORE | 10 | PENDING |
| 53 | T006214 | TRAILHEAD OUTFITTER | 10 | PENDING |
| 52 | T006106 | QUICKFUELGAS | 10 | PENDING |
| 51 | T005588 | GREEN VALLEY FOODS  #3703 | 10 | PENDING |
| 50 | T005430 | GREEN VALLEY FOODS 645 | 10 | PENDING |
| 49 | T005297 | TST*GREEN LEA | 10 | PENDING |
| 48 | T005207 | CLV*GREEN LEAF ASLADS / ST#0915 | 10 | PENDING |
| 47 | T005194 | CLV*SUNSHINE COFFEE ROASTERS | 10 | PENDING |
| 46 | T005189 | TACO FIESA * F762HG | 10 | PENDING |
| 45 | T005164 | SQ •METRO DRY CLANERS - 11QT20M0B6 | 10 | PENDING |
| 44 | T004842 | METRO DRY CLEANERS | 10 | PENDING |
| 43 | T004569 | PRECISION AUTO PARTS | 10 | PENDING |
| 42 | T004559 | GOLDEN DRAGON CHINESE * ST#3471 | 10 | PENDING |
| 41 | T004220 | CLOVER *LUXE SALON AND SPA - PORTLAND | 10 | PENDING |
| 40 | T004165 | CAREP DRUGS - SAN ANTONIO TX | 10 | PENDING |
| 39 | T004116 | TST*HOPPY TRAILS BREWING * 47 | 10 | PENDING |
| 38 | T004047 | GOLDEN DRA CHINESE * #8083 | 10 | PENDING |
| 37 | T003921 | VENMO *SUNSHINE COFFEE ROASTERS  LOC 6832 | 10 | PENDING |
| 36 | T004036 | METRO DRY CLEANERS - LOC 6463 | 10 | PENDING |
| 35 | T003670 | WEL PHARMACY LOC 3475 SAN DIEGO | 10 | PENDING |
| 34 | T003717 | SQ *MORNING BREW COFFEE | 10 | PENDING |
| 33 | T003337 | VENMO *IRONWORK  STORE 6899  TUCSON AZ | 10 | PENDING |
| 32 | T003421 | URBANTHREADS | 10 | PENDING |
| 31 | T003282 | COZY HOME GOODS BZZ0Q4Q49 | 10 | PENDING |
| 30 | T003229 | SPEEDWAY MART #7384 | 10 | PENDING |
| 29 | T003013 | CHAPTER ONE BOOKS | 10 | PENDING |
| 28 | T003002 | QUICKFUEL GAS | 10 | PENDING |
| 27 | T002615 | STR*NOODHOUSE-MESA | 10 | PENDING |
| 26 | T002520 | URBAN THR * KANSAS CITY | 10 | PENDING |
| 25 | T002757 | SQ*HOPPY TRAILS BREWING - ST#8510 | 10 | PENDING |
| 24 | T002717 | PYPL *SUNSHINE COFFEE ROAST | 10 | PENDING |
| 23 | T002703 | GADGETWORLD STORE 7495 | 10 | PENDING |
| 22 | T002657 | TST* SWEET CRUMBS BAKERY | 10 | PENDING |
| 21 | T002584 | GREEN VALLEY FOODS * LOC 6846 * S4G5V2NV | 10 | PENDING |

_… 19 more rows omitted_


## 6. Analyst approves a merchant for the ambiguous transaction


### approve_review(...)

```json
{
  "review_id": 70,
  "merchant_id": "M00277",
  "merchant_name": "Taco Fiesta",
  "status": "APPROVED"
}
```


### analyst_feedback row

```json
{
  "transaction_id": "DEMO-003",
  "selected_merchant_id": "M00277",
  "analyst_decision": "APPROVED",
  "analyst": "demo.analyst@databricks.com"
}
```


## 7. The analyst-confirmed mapping is now reused for equivalent transactions


### enrich_and_persist(ambiguous) after approval

```json
{
  "decision": "MATCHED",
  "merchant_id": "M00277",
  "merchant_name": "Taco Fiesta",
  "source": "mapping_reuse"
}
```


> After approval, the same descriptor now resolves to **MATCHED / M00277** via **mapping_reuse**.


## 8. Live operational dashboard metrics (never hard-coded)

| total_processed | matched | no_match | ambiguous | enrichment_success_rate | manual_review_pending | mapping_reuse_count | confirmed_mappings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 404 | 298 | 35 | 71 | 73.8 | 68 | 15 | 261 |


## 9. Recent enrichment activity (live from Postgres)

| transaction_id | decision | merchant_name | source | confidence |
| --- | --- | --- | --- | --- |
| DEMO-004 | MATCHED | Taco Fiesta | mapping_reuse | 1.0 |
| DEMO-003 | MATCHED | Taco Fiesta | analyst_confirmed | 1.0 |
| DEMO-002 | MATCHED | Sunshine Coffee Roasters | mapping_reuse | 0.96 |
| DEMO-001 | MATCHED | Sunshine Coffee Roasters | enrichment_workflow | 0.96 |
| T007617 | MATCHED | BrightLearn Academy | enrichment_workflow | 0.85 |
| T007734 | NO_MATCH |  | enrichment_workflow | 0.95 |
| T007395 | MATCHED | Blue Ridge Hardware | enrichment_workflow | 0.93 |
| T007472 | MATCHED | CloudStream Media | enrichment_workflow | 0.9 |
| T007684 | NO_MATCH |  | enrichment_workflow | 0.95 |
| T007382 | AMBIGUOUS |  | enrichment_workflow | 0.85 |
