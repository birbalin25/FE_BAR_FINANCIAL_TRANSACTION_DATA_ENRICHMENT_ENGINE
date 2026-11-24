# Genie Space — Example Business Questions

These eight questions are configured on the "Merchant Enrichment Analytics" Genie space
as sample questions for business users. Each maps to the governed Gold tables.

| # | Question | Primary table(s) |
|---|----------|------------------|
| 1 | How many transactions have been successfully enriched? | `gold_enrichment_results` |
| 2 | What percentage of transactions remain unmatched? | `gold_enrichment_results` |
| 3 | Which payment facilitators generate the most ambiguous transactions? | `gold_enrichment_results` |
| 4 | Which merchant categories have the lowest matching accuracy? | `gold_enrichment_results` |
| 5 | How many transactions are awaiting manual review? | `gold_enrichment_results` (decision = AMBIGUOUS) |
| 6 | What is the overall merchant enrichment success rate? | `gold_enrichment_results` |
| 7 | Which merchants have the highest transaction volumes? | `gold_merchant_metrics` |
| 8 | How has enrichment success rate changed over time? | `gold_enrichment_results` (by `processed_timestamp`) |

Model-quality questions (precision, recall, Recall@10, false-positive rate) are answered from
`gold_enrichment_quality_metrics`.

See [`evidence/genie_query_results.md`](evidence/genie_query_results.md) for actual questions
executed against the live space, the SQL Genie generated, and the returned results.
