# Phase 1 Evidence — Lakeflow Pipeline Execution

_Captured: 2026-11-24 00:24:42 UTC_

Actual execution output from the `febar_enrichment_pipeline` Spark Declarative Pipeline (serverless) on workspace `fevm-serverless-stable-iczfn0`.


## Pipeline configuration

| property | value |
| --- | --- |
| pipeline_id | 1cfd8e1e-6aaf-4e97-bd15-5ef140508ad5 |
| name | febar_enrichment_pipeline |
| catalog.schema | serverless_stable_iczfn0_catalog.febar |
| compute | serverless |
| channel | PREVIEW |
| source | lakeflow/01_bronze_ingestion.sql, 02_silver_transformation.sql, 03_gold_curatio… |

## Update runs (both COMPLETED)

| update_id | state | note |
| --- | --- | --- |
| 1e7c9a14-3715-41ad-835d-9a3b095af8c4 | COMPLETED | initial full build (bronze+silver+gold) |
| cf9c514d-a4c2-484f-ba1a-25c9a1e5d79a | COMPLETED | refresh after governance/comment update |


Observed state transitions (initial run): `CREATED → SETTING_UP_TABLES → RUNNING → COMPLETED`.


## Table inventory and row counts (live query)

| layer | table | row_count |
| --- | --- | --- |
| bronze | bronze_transactions | 8000 |
| bronze | bronze_merchants | 2220 |
| bronze | bronze_merchant_aliases | 4296 |
| silver | silver_transactions | 8000 |
| silver | silver_merchants | 2220 |
| silver | silver_merchant_aliases | 4296 |
| gold | gold_transactions | 8000 |
| gold | gold_merchants | 2220 |
| gold | gold_transaction_volume_metrics | 21 |


## Data-quality expectation results (live verification)

Expectations declared in the pipeline: `valid_txn_id` (drop null ids), `valid_amount` (amount ≥ 0), `has_descriptor` (drop null descriptors), `valid_merchant_id`, `valid_alias_id`. Live counts of violations:

| check | violations |
| --- | --- |
| transactions with NULL id | 0 |
| transactions with amount < 0 | 0 |
| transactions with NULL descriptor | 0 |
| duplicate merchant_id in silver_merchants | 0 |


## Sample — bronze_transactions (raw messy descriptors)

| transaction_id | raw_transaction_descriptor | transaction_amount | payment_facilitator |
| --- | --- | --- | --- |
| T000001 | ACME UNLISTED LLC QW29PY | 15.68 | Square |
| T000002 | QUICKFUEL GAS / SEATTLE WA | 187.54 | UNKNOWN |
| T000003 | SWEETCRUMBSBAKER#2560MADISON | 11.78 | UNKNOWN |
| T000004 | HAPPY PAWS PET SUPPLIES * ST#7355 * KANSAS CITY MO | 485.47 | UNKNOWN |
| T000005 | GREEN VALLEY OODS * #8730 * MADISON | 718.18 | UNKNOWN |
| T000006 | CHAPTER ON * LOC 7402 * PHILADELPHIA | 703.44 | UNKNOWN |
| T000007 | CLOVER *GOLDEN DRAGON CHINEES * #2120 | 131.55 | Clover |
| T000008 | NOVA UNKNOWN MERCHANT ARLINGTON VA 8UENO88 | 116.82 | Stripe |


## Sample — silver_transactions (normalized, raw preserved)

| transaction_id | raw_transaction_descriptor | normalized_descriptor |
| --- | --- | --- |
| T000001 | ACME UNLISTED LLC QW29PY | ACME UNLISTED LLC QW29PY |
| T000002 | QUICKFUEL GAS / SEATTLE WA | QUICKFUEL GAS / SEATTLE WA |
| T000003 | SWEETCRUMBSBAKER#2560MADISON | SWEETCRUMBSBAKER#2560MADISON |
| T000004 | HAPPY PAWS PET SUPPLIES * ST#7355 * KANSAS CITY MO | HAPPY PAWS PET SUPPLIES * ST#7355 * KANSAS CITY MO |
| T000005 | GREEN VALLEY OODS * #8730 * MADISON | GREEN VALLEY OODS * #8730 * MADISON |
| T000006 | CHAPTER ON * LOC 7402 * PHILADELPHIA | CHAPTER ON * LOC 7402 * PHILADELPHIA |


## Sample — gold_merchants (canonical + embedding_text)

| merchant_id | merchant_name | city | state | merchant_category | alias_count | embedding_text |
| --- | --- | --- | --- | --- | --- | --- |
| M00001 | Sunshine Coffee Roasters | Bellevue | WA | Coffee Shop | 5 | Sunshine Coffee Roasters \| CLV*SUNSHINE COFFEE \| SUNSHINE GROUP \| … |
| M00002 | Sunshine Coffee Roasters | Brooklyn | NY | Coffee Shop | 3 | Sunshine Coffee Roasters \| PAYPAL *SUNSHINE COFFEE \| Sunsh Coffee R… |
| M00003 | Sunshine Coffee Roasters | Orlando | FL | Coffee Shop | 3 | Sunshine Coffee Roasters \| Sunsh Coffe Roasters \| Sunshine Coffee \… |
| M00004 | Sunshine Coffee Roasters | Cambridge | MA | Coffee Shop | 4 | Sunshine Coffee Roasters \| SQ *SUNSHINE COFFEE \| Sunshine Cof Roast… |
| M00005 | Sunshine Coffee Roasters | Boston | MA | Coffee Shop | 3 | Sunshine Coffee Roasters \| SQ *SUNSHINE COFFEE \| Sunshine Coffe Roa… |


## Sample — gold_transaction_volume_metrics (business metric)

| transaction_month | raw_facilitator_hint | transaction_count | total_amount |
| --- | --- | --- | --- |
| 2025-08-01T00:00:00.000Z | Clover | 110 | 43686.98 |
| 2025-08-01T00:00:00.000Z | PayPal | 134 | 55645.37 |
| 2025-08-01T00:00:00.000Z | Square | 218 | 90845.58 |
| 2025-08-01T00:00:00.000Z | Stripe | 187 | 78097.72 |
| 2025-08-01T00:00:00.000Z | Toast | 108 | 46070.0 |
| 2025-08-01T00:00:00.000Z | UNKNOWN | 1846 | 785013.91 |
| 2025-08-01T00:00:00.000Z | Venmo | 118 | 48882.43 |
| 2025-09-01T00:00:00.000Z | Clover | 124 | 48767.38 |
| 2025-09-01T00:00:00.000Z | PayPal | 101 | 43878.68 |
| 2025-09-01T00:00:00.000Z | Square | 164 | 68193.6 |


## Unity Catalog governance — column comments applied (gold_merchants)

| column_name | comment |
| --- | --- |
| merchant_id | Canonical unique merchant identifier (primary key). |
| merchant_name | Canonical merchant display name. |
| address | Street address of the merchant location. |
| city | Merchant city (title-cased). |
| state | Merchant state (upper-cased 2-letter code). |
| country | Merchant country. |
| postal_code | Merchant postal / ZIP code. |
| merchant_category | Merchant business category (e.g. Coffee Shop, Grocery, Gas Station). |
| website | Merchant website URL. |
| phone_number | Merchant contact phone number. |
| alias_count | Number of known alternative names (aliases) for this merchant. |
| embedding_text | Concatenated text (name + aliases + location + category) used to generate … |
