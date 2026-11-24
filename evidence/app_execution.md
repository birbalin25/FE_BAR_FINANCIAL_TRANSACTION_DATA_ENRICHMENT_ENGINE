# Phase 5 Evidence — Databricks App Execution

_Captured: 2026-11-24 03:29:06 UTC_

The business-facing Streamlit Databricks App `febar-enrichment-app`, deployed and running on Databricks Apps. Includes proof that the DEPLOYED app executed the full enrichment workflow server-side (as its service principal).


## Deployment

| property | value |
| --- | --- |
| app name | febar-enrichment-app |
| url | https://febar-enrichment-app-7474646684279456.aws.databricksapps.com |
| service principal | 3bd563db-fee1-4bfa-b642-3433bdb76267 |
| framework | Streamlit (Databricks Apps runtime, Python 3.11) |
| deployment state | SUCCEEDED — 'App started successfully' |
| compute / app status | ACTIVE / RUNNING |


Build + startup log excerpt (from `databricks apps logs`):

```
[BUILD] Successfully installed ... openai-3.58.0 psycopg-3.3.9 databricks-sdk-0.170.0 databricks-vectorsearch-0.82 ...
[BUILD] [INFO] Requirements installed successfully.
[BUILD] [INFO] Starting app with command: [streamlit run app/app.py]
[APP]   You can now view your Streamlit app in your browser.
[APP]   URL: http://0.0.0.0:8000
[BUILD] [INFO] Deployment successful
[HTTP] ... "GET / HTTP/1.1" 200 891 "-" "curl/8.7.1"   (authenticated request)
```


## Resource & permission wiring (app service principal)

| item | detail |
| --- | --- |
| Lakebase resource | postgres resource attached (branch=production, db=databricks-postgres) |
| Lakebase token | minted in-app via POST /api/2.0/postgres/credentials (SDK api_client) |
| Lakebase grants | febar_ops: USAGE+CREATE on schema; ALL on tables+sequences; default privileges … |
| Unity Catalog | USE CATALOG + USE SCHEMA + SELECT granted to SP |
| SQL warehouse | CAN_USE granted to SP (DATABRICKS_WAREHOUSE_ID env) |
| Foundation Models / Vector Search | queried via SDK OAuth token (SP) |


## Proof the DEPLOYED app executed the full enrichment workflow

A websocket session was opened to the running app (Databricks OAuth proxy accepts a bearer token). With the `FEBAR_APP_SELFTEST` hook enabled, the app ran one real enrichment **server-side as its service principal** and persisted it to Lakebase. The row below was written by the deployed app's runtime (verified by querying Lakebase externally) with `source = enrichment_workflow`, meaning the app executed GenAI entity recognition → Vector Search → LLM judge → Lakebase persistence:

| transaction_id | raw_descriptor | decision | merchant_id | merchant_name | confidence | source |
| --- | --- | --- | --- | --- | --- | --- |
| APP-SELFTEST | SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY | MATCHED | M00028 | Sunshine Coffee Roasters | 0.96 | enrichment_workflow |


**Entities the app extracted (GenAI, in the deployed runtime):**

```json
{
  "city": "Larchmont",
  "state": "NY",
  "country": "USA",
  "merchant_name": "Sunshine Coffee Roasters",
  "order_identifier": null,
  "store_identifier": null,
  "payment_facilitator": "Square"
}
```


Server log confirming the session + clean load after the fix:

```
[APP]   URL: http://0.0.0.0:8000
[HTTP] ... "GET /_stcore/stream HTTP/1.1" 101 0 "-" "Python/3.13 websockets/17.4"
(no app exceptions after the clean redeploy)
```


## Live operational dashboard (served by the app from Lakebase)

| total_processed | matched | no_match | ambiguous | enrichment_success_rate | manual_review_pending | mapping_reuse_count | confirmed_mappings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 405 | 299 | 35 | 71 | 73.8 | 68 | 15 | 261 |


## Application sections (code map)

| section | behavior |
| --- | --- |
| Merchant Enrichment | enter/select descriptor → common.ops.enrich_and_persist (reuse check → extract … |
| Operations Dashboard | lakebase.persistence.dashboard_metrics() + recent_activity() — live, never hard… |
| Manual Review | list_review_queue / approve_review / reject_review — persists analyst decisions… |
| Genie Analytics | links to the configured Genie space (01f1e7b38d1e1b228419f9357e1ea6c5) |


## Interactive UI access

The app URL is protected by Databricks OAuth SSO (screenshot: `app_login_redirect.png`). To use the UI interactively: open the app URL, sign in with Databricks SSO, and use the four sections above. Programmatic/headless execution evidence (server-side) is captured above.
