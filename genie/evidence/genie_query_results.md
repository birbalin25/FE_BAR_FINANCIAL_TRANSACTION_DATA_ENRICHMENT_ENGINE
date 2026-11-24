# Phase 4 Evidence — Genie Space Natural-Language Queries

_Captured: 2026-11-24 03:04:24 UTC_

Actual questions executed against the configured Genie space `01f1e7b38d1e1b228419f9357e1ea6c5` via the Genie Conversation API. 5/5 returned answers. Space URL: https://fevm-serverless-stable-iczfn0.cloud.databricks.com/genie/rooms/01f1e7b38d1e1b228419f9357e1ea6c5



---

## Q1. How many transactions have been successfully enriched?

**Status:** `COMPLETED`


**Genie answer:** There are **298** transactions with decision **MATCHED**, which means **298** transactions have been successfully enriched. Based on the result shown, the successfully enriched transaction count is **298**.


**Generated SQL:**

```sql
SELECT COUNT(*) AS `successfully_enriched_transactions`
FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
WHERE `decision` = 'MATCHED'
```


**Query result:**

| successfully_enriched_transactions |
| --- |
| 298 |


---

## Q2. What percentage of transactions remain unmatched?

**Status:** `COMPLETED`


**Genie answer:** **8.66336633663366%** of transactions remain unmatched, based on transactions with decision = **NO_MATCH** in `gold_enrichment_results`. This means the unmatched rate is about **8.66%** overall in the result shown.


**Generated SQL:**

```sql
SELECT try_divide(100.0 * SUM(CASE WHEN `decision` = 'NO_MATCH' THEN 1 ELSE 0 END),COUNT(*)) AS `unmatched_percentage`
FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
```


**Query result:**

| unmatched_percentage |
| --- |
| 8.66336633663366 |


---

## Q3. Which payment facilitators generate the most ambiguous transactions?

**Status:** `COMPLETED`


**Genie answer:** **Toast** generates the most ambiguous transactions with **6**. Examples include:
- **Toast** — **6** ambiguous transactions
- **Clover** — **4**
- **Square** — **4**
- **PayPal** — **2**
- **Venmo** — **2**
Across the 6 facilitators shown, ambiguous transaction counts range from **1** to **6**, with **Toast** clearly leading and **Clover** and **Square** tied just behind it.


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
  `payment_facilitator`,
  `ambiguous_transactions`,
  `facilitator_rank`
FROM ranked_facilitators
ORDER BY `facilitator_rank` ASC, `payment_facilitator` ASC
```


**Query result:**

| payment_facilitator | ambiguous_transactions | facilitator_rank |
| --- | --- | --- |
| Toast | 6 | 1 |
| Clover | 4 | 2 |
| Square | 4 | 3 |
| PayPal | 2 | 4 |
| Venmo | 2 | 5 |
| Stripe | 1 | 6 |


---

## Q4. What is the overall merchant enrichment success rate?

**Status:** `COMPLETED`


**Genie answer:** The overall merchant enrichment success rate is **73.76237623762376%**, based on the share of transactions with decision **MATCHED** out of all transactions in `gold_enrichment_results`. This means **73.76237623762376%** of transactions were successfully linked to a single canonical merchant.


**Generated SQL:**

```sql
SELECT try_divide(100.0 * SUM(CASE WHEN `decision` = 'MATCHED' THEN 1 ELSE 0 END),COUNT(*)) AS `enrichment_success_rate` FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_enrichment_results`
```


**Query result:**

| enrichment_success_rate |
| --- |
| 73.76237623762376 |


---

## Q5. Which merchants have the highest transaction volumes?

**Status:** `COMPLETED`


**Genie answer:** The merchant with the highest transaction volume is **IronWorks Fitness** (merchant ID **M01733**) in the **Fitness** category, with **14** total transactions. Based on the result shown, **IronWorks Fitness** is the top-volume merchant in `gold_merchant_metrics`.


**Generated SQL:**

```sql
WITH ranked_merchants AS (
  SELECT
    `merchant_id`,
    `merchant_name`,
    `merchant_category`,
    `total_transactions`,
    RANK() OVER (ORDER BY `total_transactions` DESC, `merchant_name` ASC) AS `volume_rank`
  FROM `serverless_stable_iczfn0_catalog`.`febar`.`gold_merchant_metrics`
  WHERE `merchant_name` IS NOT NULL
    AND `total_transactions` IS NOT NULL
)
SELECT
  `merchant_id`,
  `merchant_name`,
  `merchant_category`,
  `total_transactions`
FROM ranked_merchants
WHERE `volume_rank` = 1
ORDER BY `merchant_name` ASC;
```


**Query result:**

| merchant_id | merchant_name | merchant_category | total_transactions |
| --- | --- | --- | --- |
| M01733 | IronWorks Fitness | Fitness | 14 |
