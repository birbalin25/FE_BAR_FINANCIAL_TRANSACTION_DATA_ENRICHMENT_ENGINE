# Phase 4 Evidence — Genie Space Natural-Language Queries

_Captured: 2026-11-25 18:44:44 UTC_

Actual questions executed against the configured Genie space `01f1e7b38d1e1b228419f9357e1ea6c5` via the Genie Conversation API. 5/5 returned answers. Space URL: https://fevm-serverless-stable-iczfn0.cloud.databricks.com/genie/rooms/01f1e7b38d1e1b228419f9357e1ea6c5



---

## Q1. How many transactions have been successfully enriched?

**Status:** `COMPLETED`


**Genie answer:** There are **299** successfully enriched transactions, based on transactions with decision = **MATCHED**. In this result set, the count of successfully enriched transactions is both the minimum and maximum value at **299** because the query returned **1** row.


**Generated SQL:**

```sql
SELECT COUNT(*) AS `successfully_enriched_transactions`
FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
WHERE `decision` = 'MATCHED'
```


**Query result:**

| successfully_enriched_transactions |
| --- |
| 299 |


---

## Q2. What percentage of transactions remain unmatched?

**Status:** `COMPLETED`


**Genie answer:** **8.64197530864198%** of transactions remain unmatched, based on transactions with decision = **NO_MATCH** in `gold_enrichment_results`. This means the unmatched rate is about **8.64%** across the full result set used in the query.


**Generated SQL:**

```sql
SELECT try_divide(100.0 * SUM(CASE WHEN `decision` = 'NO_MATCH' THEN 1 ELSE 0 END),COUNT(*)) AS `unmatched_rate_percentage`
FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
```


**Query result:**

| unmatched_rate_percentage |
| --- |
| 8.64197530864198 |


---

## Q3. Which payment facilitators generate the most ambiguous transactions?

**Status:** `COMPLETED`


**Genie answer:** Would you prefer to see payment facilitators ranked by the percentage of ambiguous transactions instead of the total count?


**Generated SQL:**

```sql
WITH facilitator_counts AS (
  SELECT
    `payment_facilitator`,
    COUNT(*) AS `ambiguous_transactions`
  FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
  WHERE `decision` = 'AMBIGUOUS'
    AND `payment_facilitator` IS NOT NULL
  GROUP BY `payment_facilitator`
), ranked_facilitators AS (
  SELECT
    `payment_facilitator`,
    `ambiguous_transactions`,
    RANK() OVER (ORDER BY `ambiguous_transactions` DESC, `payment_facilitator` ASC) AS `facilitator_rank`
  FROM facilitator_counts
)
SELECT
  `facilitator_rank`,
  `payment_facilitator`,
  `ambiguous_transactions`
FROM ranked_facilitators
ORDER BY `facilitator_rank` ASC, `payment_facilitator` ASC;
```


**Query result:**

| facilitator_rank | payment_facilitator | ambiguous_transactions |
| --- | --- | --- |
| 1 | Toast | 6 |
| 2 | Clover | 4 |
| 3 | Square | 4 |
| 4 | PayPal | 2 |
| 5 | Venmo | 2 |
| 6 | Stripe | 1 |


---

## Q4. What is the overall merchant enrichment success rate?

**Status:** `COMPLETED`


**Genie answer:** The overall merchant enrichment success rate is **73.83%**, based on the share of transactions with decision = **MATCHED** out of all transactions in `gold_enrichment_results`. This means **73.83%** of transactions were reliably linked to exactly one canonical merchant.


**Generated SQL:**

```sql
SELECT try_divide(100.0 * SUM(CASE WHEN `decision` = 'MATCHED' THEN 1 ELSE 0 END),COUNT(*)) AS `enrichment_success_rate`
FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
```


**Query result:**

| enrichment_success_rate |
| --- |
| 73.82716049382716 |


---

## Q5. Which merchants have the highest transaction volumes?

**Status:** `COMPLETED`


**Genie answer:** The merchant with the **highest transaction volume** is **IronWorks Fitness** (merchant ID **M01733**), in the **Fitness** category, with **14 total transactions** and **14 matched transactions**. In this result, **IronWorks Fitness** is the top-volume merchant and all **14 of 14** transactions were matched.


**Generated SQL:**

```sql
WITH ranked_merchants AS (
  SELECT
    `merchant_id`,
    `merchant_name`,
    `merchant_category`,
    `total_transactions`,
    `matched_transactions`,
    RANK() OVER (ORDER BY `total_transactions` DESC, `merchant_name` ASC) AS `volume_rank`
  FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_merchant_metrics`
  WHERE `merchant_name` IS NOT NULL
    AND `total_transactions` IS NOT NULL
)
SELECT
  `merchant_id`,
  `merchant_name`,
  `merchant_category`,
  `total_transactions`,
  `matched_transactions`
FROM ranked_merchants
WHERE `volume_rank` = 1
ORDER BY `total_transactions` DESC, `merchant_name` ASC
```


**Query result:**

| merchant_id | merchant_name | merchant_category | total_transactions | matched_transactions |
| --- | --- | --- | --- | --- |
| M01733 | IronWorks Fitness | Fitness | 14 | 14 |
