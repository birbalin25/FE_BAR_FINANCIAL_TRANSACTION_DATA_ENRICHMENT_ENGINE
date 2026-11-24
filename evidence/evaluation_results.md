# Phase 6 Evidence — Enrichment Evaluation (vs. held-out ground truth)

_Captured: 2026-11-24 02:54:32 UTC_

Full evaluation over 400 held-out transactions. Models: chat `databricks-claude-sonnet-5-5`, embeddings `databricks-gte-large-en`. Wall time 239s. MLflow logged: True.


## Entity recognition accuracy

| metric | value % |
| --- | --- |
| Payment-facilitator extraction accuracy | 43.1 |
| Merchant-name extraction accuracy | 89.17 |
| Location (city+state) extraction accuracy | 53.33 |


## Candidate retrieval (Vector Search)

| metric | value % |
| --- | --- |
| Recall@10 | 99.17 |
| Correct merchant NOT retrieved | 0.83 |


## Entity linkage (LLM judge)

| metric | value % |
| --- | --- |
| Matching precision | 100.0 |
| Matching recall | 91.67 |
| False-positive rate (wrong MATCHED / all MATCHED) | 0.0 |
| Forced matches on non-matchable truths (count) | 0 |
| NO_MATCH classification accuracy | 100.0 |
| AMBIGUOUS classification accuracy | 98.75 |


## Operational metrics

| metric | value |
| --- | --- |
| Enrichment success rate (system MATCHED) | 55.0% |
| Manual review rate (system AMBIGUOUS) | 23.5% |
| Avg end-to-end latency | 4592.0 ms |
| Total LLM invocations | 800 |


## Confusion detail (counts)

| truth_matched | truth_no_match | truth_ambiguous | system_matched | true_positives | false_positives | recall_denom | recall_hits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 240 | 80 | 80 | 220 | 220 | 0 | 240 | 238 |
