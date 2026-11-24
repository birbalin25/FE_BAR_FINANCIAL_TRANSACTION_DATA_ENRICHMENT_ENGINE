# Genie Space — Setup & Access Instructions

## Prerequisites

- A Pro or Serverless SQL warehouse (this project uses warehouse `e9846c65aa767493`).
- The three Unity Catalog Gold tables must exist and be populated:
  - `serverless_stable_iczfn0_catalog.febar.gold_enrichment_results`
  - `serverless_stable_iczfn0_catalog.febar.gold_merchant_metrics`
  - `serverless_stable_iczfn0_catalog.febar.gold_enrichment_quality_metrics`
  (Produced by `lakebase/sync_to_uc.py` and `evaluation/evaluate_enrichment.py`.)
- Databricks Assistant enabled for the workspace.
- `CAN USE` on the SQL warehouse and `SELECT` on the Gold tables.

## Automated creation

The space is created and configured programmatically — data sources, table descriptions,
business instructions, and the eight sample questions — via the Genie Spaces REST API:

```bash
PYTHONPATH=. python3 genie/create_genie_space.py
```

This calls `POST /api/2.0/genie/spaces` with a `serialized_space` (version 2) payload and writes
the resulting `genie_space_id` and URL into `config/resources.json`.

## Accessing the space

- **URL:** `https://fevm-serverless-stable-iczfn0.cloud.databricks.com/genie/rooms/<genie_space_id>`
  (the exact id is recorded in `config/resources.json` and the root README after creation).
- From the Databricks App: the **Genie Analytics** section links directly to the space.

## Validation

`genie/evidence/genie_query_results.md` contains actual questions executed against the space via
the Genie Conversation API, the SQL Genie generated, and the returned results.
