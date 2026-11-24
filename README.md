# Financial Transaction Data Enrichment Engine

> AI-powered merchant identification that turns messy card-transaction descriptors into
> standardized merchant identities — built end-to-end on the Databricks Data Intelligence Platform.

| | |
|---|---|
| **Project** | Financial Transaction Data Enrichment Engine |
| **Industry** | Banking & Financial Services — Retail Banking / Card Issuing |
| **Target customer** | Large US retail bank / card issuer |
| **Business owner** | Head of Payments Operations |
| **Executive sponsor** | Chief Operating Officer (COO) |
| **Workspace** | `fevm-serverless-stable-iczfn0` (FE Vending Machine) |
| **Catalog.Schema** | `serverless_stable_iczfn0_catalog.febar` |

---

## 1. Project Overview

A large retail bank processes millions of card transactions every month. The transaction
descriptors it receives from payment networks, merchants, and payment facilitators are
inconsistent, abbreviated, truncated, or ambiguous, so the bank often cannot reliably identify
the real merchant behind a transaction. This project is a working prototype that uses GenAI,
vector retrieval, and an LLM judge to transform unstructured descriptors into governed,
standardized merchant identities, served operationally and exposed for self-service analytics.

All six mandatory Databricks capabilities are integrated into one business solution:
**Lakeflow**, **Unity Catalog**, **Lakebase**, **GenAI + Vector Search**, **Genie**, and **Databricks Apps** (with **MLflow** for tracking/evaluation).

## 2. Business Problem

Transaction descriptors such as the following all refer to the *same* merchant:

```
SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY
SQUARE SUNSHINE COFFEE LARCHMONT
SQ SUNSHINE COFFEE ROASTERS
SUNSHINE COFFEE #1234 LARCHMONT NY
```

Because the descriptor is unstructured and noisy (facilitator prefixes like `SQ *`/`PAYPAL *`,
abbreviations, misspellings, truncation, store numbers, order IDs, missing location), analysts
must manually investigate a large share of transactions. Accurate merchant identification powers
fraud detection, dispute resolution, spend analytics, merchant-level reporting, and customer
experience — so the operational pain is both costly and strategically important.

**Illustrative business assumptions** (not industry benchmarks):

- 10,000,000 card transactions processed monthly
- 15% contain inconsistent / unclear merchant descriptors (1,500,000)
- 8% of those require manual investigation (120,000)
- ~2 minutes per manual investigation → **~4,000 analyst hours / month**

**Expected outcome:** automatically enrich the majority of descriptors, route only genuinely
ambiguous cases to analysts, and continuously reuse confirmed mappings — sharply reducing manual
investigation hours while improving identification accuracy.

## 3. Business KPIs

| KPI | Definition |
|---|---|
| Enrichment success rate | % of processed transactions with a confident `MATCHED` decision |
| Matching precision | Of `MATCHED` decisions, fraction that are correct (per ground truth) |
| Recall@10 | % of transactions where the correct merchant is in the Vector Search top-10 |
| False-positive rate | Fraction of `MATCHED` decisions that are wrong (primary risk metric) |
| Manual review rate | % of transactions routed to `AMBIGUOUS` manual review |
| Manual investigation hours | Estimated analyst hours saved vs. the all-manual baseline |

Actual measured values are in [`evidence/evaluation_results.md`](evidence/evaluation_results.md) (Phase 6).

## 4. Solution Architecture

```mermaid
flowchart TD
    SYN["Synthetic data<br/>(transactions, merchants, aliases, ground truth)"] --> VOL["UC Volume<br/>raw_landing"]
    VOL --> LF["Lakeflow Spark Declarative Pipeline"]
    subgraph UC["Unity Catalog (governed)"]
      B["Bronze<br/>raw streaming tables"] --> S["Silver<br/>cleaned + embedding_text"] --> G["Gold<br/>gold_transactions / gold_merchants"]
    end
    LF --> B
    G --> ER["GenAI Entity Recognition<br/>(LLM structured output)"]
    ER --> VS["Databricks Vector Search<br/>top-10 candidates"]
    VS --> JUDGE["LLM Entity Judge<br/>MATCHED / NO_MATCH / AMBIGUOUS"]
    MAP[("Lakebase<br/>merchant_mapping")] -. "reuse check (fingerprint)" .-> ER
    JUDGE --> RES["Enrichment result"]
    RES --> LB[("Lakebase (Postgres)<br/>operational serving")]
    LB --> SYNC["sync_to_uc"] --> GA["UC Gold analytics<br/>gold_enrichment_results / _merchant_metrics / _quality_metrics"]
    GA --> GENIE["Genie Space<br/>NL analytics"]
    LB --> APP["Databricks App"]
    GENIE --> APP
    APP --> USER(["Business user / analyst"])
    MLF["MLflow tracking + evaluation"] -.-> ER
    MLF -.-> JUDGE
```

**End-to-end journey:** synthetic raw files land in a UC Volume → Lakeflow ingests and curates
them through Bronze/Silver/Gold in Unity Catalog → for each transaction, the system first checks
Lakebase for a confirmed mapping; on a miss it runs LLM entity recognition, retrieves the top-10
merchant candidates from Vector Search, and an LLM judge makes the final decision → results are
persisted operationally in Lakebase → a sync job publishes outcomes to Unity Catalog Gold → Genie
answers natural-language questions over the Gold tables → the Databricks App ties the workflow
together for the payments operations team. MLflow tracks and evaluates the GenAI components.

## 5. Databricks Components

| Component | Role in this solution | Status |
|---|---|---|
| **Lakeflow** (Spark Declarative Pipelines) | Ingest + transform raw data into Bronze/Silver/Gold | ✅ Implemented & executed |
| **Unity Catalog** | Governance: catalog/schema, table + column descriptions, Gold analytics tables | ✅ Implemented |
| **GenAI (Foundation Models)** | Entity recognition + LLM judge via `databricks-claude-sonnet-5-5` | ⏳ Phase 2 |
| **Vector Search** | Retrieve top-10 merchant candidates (`databricks-gte-large-en` embeddings) | ⏳ Phase 2 |
| **MLflow** | Track GenAI calls + evaluate against ground truth | ⏳ Phase 2 / 6 |
| **Lakebase** (Postgres OLTP) | Operational serving: results, confirmed mappings, review queue, feedback | ⏳ Phase 3 |
| **Genie** | Natural-language analytics over governed Gold tables | ⏳ Phase 4 |
| **Databricks Apps** | Business-facing app: enrichment, dashboard, manual review, Genie access | ⏳ Phase 5 |

## 6. Repository Structure

```
financial-transaction-enrichment/
├── README.md                      # This file — master documentation
├── requirements.txt               # Python dependencies (installed in Databricks runtimes/app)
├── config/
│   ├── project_config.yaml        # All parameters (catalog, schema, endpoints, resource names)
│   └── resources.json             # Live resource identifiers created by the project
├── common/                        # Shared helpers (config loader, CLI/SQL wrapper, evidence)
├── data_generation/
│   └── generate_synthetic_data.py # Deterministic synthetic data generator (seed=42)
├── lakeflow/
│   ├── 01_bronze_ingestion.sql    # Auto Loader streaming tables
│   ├── 02_silver_transformation.sql
│   ├── 03_gold_curation.sql
│   └── apply_governance.py        # Idempotent UC column comments
├── entity_recognition/            # LLM entity extraction (Phase 2)
├── vector_search/                 # Index creation + candidate retrieval (Phase 2)
├── entity_linkage/                # LLM judge (Phase 2)
├── evaluation/                    # MLflow evaluation against ground truth (Phase 6)
├── lakebase/                      # Operational Postgres tables + persistence + sync (Phase 3)
├── genie/                         # Genie space creation + instructions + evidence (Phase 4)
├── app/                           # Databricks App (Phase 5)
└── evidence/                      # Actual execution outputs (text/markdown)
```

## 7. Prerequisites and Workspace Configuration

- A Databricks workspace with: serverless SQL warehouse, Foundation Model APIs, Vector Search,
  Lakebase (Database Instances), Genie, and Databricks Apps enabled. This prototype runs on the
  FE Vending Machine workspace `fevm-serverless-stable-iczfn0`.
- Databricks CLI ≥ v0.21 authenticated with an OAuth profile (`fevm` here).
- Permissions to create: UC volumes/tables, Lakeflow pipelines, Vector Search endpoints/indexes,
  Lakebase instances, Genie spaces, and Apps.
- Foundation model endpoints used: chat `databricks-claude-sonnet-5-5`, embeddings
  `databricks-gte-large-en` (both available in-workspace; parameterized in `project_config.yaml`).

> **Note (IP access list):** this workspace enforces an IP ACL. If CLI calls intermittently
> return `Source IP ... is blocked by Databricks IP ACL`, add your current egress IP to the
> workspace IP access list (Admin → Security). Operations retried once the IP was allow-listed.

## 8. Installation and Setup

```bash
# 1. Authenticate (SSO)
databricks auth login https://fevm-serverless-stable-iczfn0.cloud.databricks.com --profile fevm

# 2. (Local orchestration) Python 3.11+ with stdlib + openai + psycopg already present.
#    Heavy compute runs inside Databricks; local scripts shell out to the CLI.
#    Run local scripts from the repo root with:  PYTHONPATH=. python3 <script>

# 3. Configuration is centralized in config/project_config.yaml and overridable via
#    FEBAR_<SECTION>_<KEY> environment variables.
```

## 9. Synthetic Data Generation

```bash
python3 data_generation/generate_synthetic_data.py      # deterministic, seed=42
```

Generates four internally-consistent datasets (no real/customer/Mastercard data):

| Dataset | Rows | Key fields |
|---|---|---|
| `merchants.csv` | 2,220 | merchant_id, merchant_name, address, city, state, country, postal_code, merchant_category, website, phone_number |
| `merchant_aliases.csv` | 4,296 | alias_id, merchant_id, alias_name, alias_type |
| `transactions.csv` | 8,000 | transaction_id, transaction_date, transaction_amount, currency, raw_transaction_descriptor, country, payment_facilitator |
| `ground_truth.csv` | 400 | transaction_id, expected_decision, expected_merchant_id, expected_merchant_name, expected_payment_facilitator, expected_city, expected_state |

Transactions deliberately include facilitator prefixes, abbreviations, misspellings, truncation,
store numbers, order IDs, punctuation noise, missing location, and unmatchable descriptors.
The decision mix is ~80% MATCHED / ~12% AMBIGUOUS / ~8% NO_MATCH. **Ground truth is used only for
evaluation and is never exposed to the enrichment logic** (it is not loaded by the pipeline).

## 10. Lakeflow Execution

A serverless **Spark Declarative Pipeline** (`febar_enrichment_pipeline`, id
`1cfd8e1e-6aaf-4e97-bd15-5ef140508ad5`) ingests the volume files and builds the medallion layers:

- **Bronze** — `bronze_transactions`, `bronze_merchants`, `bronze_merchant_aliases`: Auto Loader
  streaming tables (`STREAM read_files`) with data-quality expectations.
- **Silver** — `silver_transactions` (normalized descriptor, raw preserved), `silver_merchants`
  (deduped, normalized location, **embedding_text** prepared), `silver_merchant_aliases` (deduped).
- **Gold** — `gold_transactions`, `gold_merchants` (canonical master consumed by Vector Search),
  `gold_transaction_volume_metrics`.

Deploy & run:

```bash
databricks workspace import-dir ./lakeflow /Workspace/Users/<you>/febar/lakeflow --overwrite --profile fevm
databricks pipelines start-update 1cfd8e1e-6aaf-4e97-bd15-5ef140508ad5 --profile fevm
python3 lakeflow/apply_governance.py      # apply UC column comments (idempotent)
```

**Execution evidence:** [`evidence/pipeline_execution.md`](evidence/pipeline_execution.md) — both
updates `COMPLETED`, all 9 tables populated (8,000 / 2,220 / 4,296 rows), 0 data-quality violations.

## 11. Merchant Entity Recognition
_⏳ Phase 2 — see `entity_recognition/`._

## 12. Vector Search and LLM Judge
_⏳ Phase 2 — see `vector_search/` and `entity_linkage/`._

## 13. Lakebase Operational Serving
_⏳ Phase 3 — see `lakebase/`._

## 14. Unity Catalog Analytics
_⏳ Phase 4 — Gold analytics tables populated from Lakebase via `lakebase/sync_to_uc.py`._

## 15. Genie Agent Configuration and Usage
_⏳ Phase 4 — see `genie/`._

## 16. Databricks App Deployment
_⏳ Phase 5 — see `app/`._

## 17. End-to-End Demonstration
_⏳ Phase 5._

## 18. Evaluation Results
_⏳ Phase 6 — see `evidence/evaluation_results.md`._

## 19. Execution Evidence

| Evidence | File |
|---|---|
| Lakeflow pipeline execution | [`evidence/pipeline_execution.md`](evidence/pipeline_execution.md) ✅ |
| Enrichment examples (extraction + retrieval + judge) | `evidence/enrichment_examples.md` ⏳ |
| Evaluation results | `evidence/evaluation_results.md` ⏳ |
| Lakebase operations | `evidence/lakebase_execution.md` ⏳ |
| Genie queries & results | `genie/evidence/genie_query_results.md` ⏳ |
| App execution | `evidence/app_execution.md` ⏳ |

## 20. Known Limitations and Future Enhancements

- Prototype scope: data is synthetic; volumes are illustrative.
- See each phase section for component-specific limitations as they are implemented.

---

_Built as an FE Bar prototype demonstrating an integrated Databricks solution for retail banking merchant enrichment._
