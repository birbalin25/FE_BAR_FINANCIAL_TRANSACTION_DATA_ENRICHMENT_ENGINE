"""Financial Transaction Data Enrichment Engine — Databricks App (Streamlit).

Business-facing app for the Head of Payments Operations and the investigation team.
Four sections:
  1. Merchant Enrichment  — submit/select a descriptor, run the full workflow, show result
  2. Operations Dashboard — live metrics from Lakebase (never hard-coded)
  3. Manual Review        — triage AMBIGUOUS transactions, approve/reject, persist
  4. Genie Analytics      — link to the configured Genie space

Reuses the exact same enrichment + persistence modules as the batch/evaluation code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# make the repo-root modules importable when deployed as app source
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import CFG                      # noqa: E402
from common.dbx import rows as uc_rows             # noqa: E402
from common.ops import enrich_and_persist          # noqa: E402
from lakebase import persistence as lb             # noqa: E402

RESOURCES = json.loads((Path(__file__).resolve().parent.parent / "config" / "resources.json").read_text())

st.set_page_config(page_title="Merchant Enrichment Engine", page_icon="🏦", layout="wide")


@st.cache_resource
def _bootstrap():
    lb.init_schema()
    return True


def _candidate_table(cands: list[dict]):
    if not cands:
        st.info("No candidates retrieved.")
        return
    st.dataframe(
        [{"merchant_id": c.get("merchant_id"), "merchant_name": c.get("merchant_name"),
          "city": c.get("city"), "state": c.get("state"),
          "category": c.get("merchant_category"),
          "similarity": c.get("similarity_score")} for c in cands],
        use_container_width=True, hide_index=True,
    )


DECISION_COLOR = {"MATCHED": "green", "NO_MATCH": "red", "AMBIGUOUS": "orange"}


def show_result(r: dict):
    dec = r["decision"]
    c = DECISION_COLOR.get(dec, "gray")
    st.markdown(f"### Decision: :{c}[{dec}]")
    cols = st.columns(4)
    cols[0].metric("Merchant ID", r.get("merchant_id") or "—")
    cols[1].metric("Merchant", (r.get("merchant_name") or "—"))
    cols[2].metric("Confidence", f"{r.get('confidence'):.2f}" if r.get("confidence") is not None else "—")
    cols[3].metric("Source", r.get("source") or "—")
    st.caption(f"Reason: {r.get('reason')}")

    with st.expander("Original descriptor & extracted entities", expanded=True):
        st.code(r["raw_descriptor"], language=None)
        st.caption(f"Fingerprint: `{r['descriptor_fingerprint']}`")
        if r.get("extracted_entities"):
            st.json(r["extracted_entities"])
    if r.get("source") != "mapping_reuse":
        with st.expander("Top-10 Vector Search candidates", expanded=True):
            _candidate_table(r.get("candidates") or [])
    st.caption(f"Latency: {r.get('latency_ms')} ms · LLM calls: {r.get('llm_calls')}")


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def section_enrichment():
    st.header("🔎 Merchant Enrichment")
    st.write("Submit a raw transaction descriptor or pick an existing transaction. "
             "The engine checks Lakebase for a confirmed mapping, then runs GenAI "
             "entity recognition → Vector Search (top-10) → LLM judge.")

    mode = st.radio("Input", ["Enter a descriptor", "Pick an existing transaction"], horizontal=True)
    descriptor, txn_id = None, None
    if mode == "Enter a descriptor":
        descriptor = st.text_input("Transaction descriptor",
                                   value="SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY")
    else:
        try:
            sample = uc_rows(f"SELECT transaction_id, raw_transaction_descriptor FROM "
                             f"{CFG.table('gold_transactions')} ORDER BY transaction_id LIMIT 50")
            choice = st.selectbox("Transaction", sample,
                                  format_func=lambda r: f"{r['transaction_id']} — {r['raw_transaction_descriptor']}")
            if choice:
                descriptor = choice["raw_transaction_descriptor"]
                txn_id = choice["transaction_id"]
        except Exception as e:  # noqa: BLE001
            st.warning(f"Could not load transactions: {e}")
            descriptor = st.text_input("Transaction descriptor")

    if st.button("Run enrichment", type="primary") and descriptor:
        with st.spinner("Enriching…"):
            r = enrich_and_persist(descriptor, transaction_id=txn_id)
        show_result(r)


def section_dashboard():
    st.header("📊 Operations Dashboard")
    m = lb.dashboard_metrics()
    c = st.columns(4)
    c[0].metric("Total processed", m["total_processed"])
    c[1].metric("Matched", m["matched"])
    c[2].metric("Ambiguous (review)", m["ambiguous"])
    c[3].metric("No match", m["no_match"])
    c = st.columns(4)
    c[0].metric("Enrichment success rate", f"{m['enrichment_success_rate']}%")
    c[1].metric("Pending manual review", m["manual_review_pending"])
    c[2].metric("Mapping reuse count", m["mapping_reuse_count"])
    c[3].metric("Confirmed mappings", m["confirmed_mappings"])

    st.subheader("Recent enrichment activity")
    act = lb.recent_activity(15)
    if act:
        st.dataframe([{"transaction_id": a["transaction_id"], "decision": a["decision"],
                       "merchant": a["merchant_name"], "confidence": a["confidence"],
                       "source": a["source"], "ts": str(a["processed_timestamp"])} for a in act],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No activity yet — run an enrichment.")


def section_review():
    st.header("🧾 Manual Review Queue")
    st.write("Ambiguous transactions routed here for analyst resolution. "
             "Approving a merchant confirms a reusable mapping for equivalent future transactions.")
    queue = lb.list_review_queue("PENDING")
    if not queue:
        st.success("No transactions pending review. 🎉")
        return
    for item in queue:
        with st.expander(f"Review #{item['review_id']} — {item['raw_descriptor']}", expanded=False):
            st.caption(f"Transaction: {item.get('transaction_id')} · "
                       f"Fingerprint: `{item['descriptor_fingerprint']}`")
            if item.get("extracted_entities"):
                st.json(item["extracted_entities"], expanded=False)
            cands = item.get("candidate_merchants") or []
            _candidate_table(cands)
            options = {f"{c['merchant_id']} — {c['merchant_name']} ({c.get('city')}, {c.get('state')})":
                       c["merchant_id"] for c in cands}
            col1, col2 = st.columns([3, 1])
            pick = col1.selectbox("Select correct merchant", list(options.keys()),
                                  key=f"pick_{item['review_id']}")
            if col1.button("✅ Approve mapping", key=f"appr_{item['review_id']}"):
                lb.approve_review(item["review_id"], options[pick], analyst=_current_user())
                st.success(f"Approved → {options[pick]}. Mapping confirmed for reuse.")
                st.rerun()
            if col2.button("❌ Reject", key=f"rej_{item['review_id']}"):
                lb.reject_review(item["review_id"], analyst=_current_user())
                st.warning("Rejected.")
                st.rerun()


def section_genie():
    st.header("💬 Genie — Natural-language Analytics")
    space_id = RESOURCES.get("genie_space_id")
    url = RESOURCES.get("genie_space_url")
    st.write("Ask business questions in natural language over the governed Unity Catalog "
             "Gold tables (enrichment outcomes, merchant metrics, quality metrics).")
    if space_id:
        st.success(f"Genie space configured: `{space_id}`")
        st.link_button("Open Genie Space ↗", url or
                       f"{RESOURCES['workspace_host']}/genie/rooms/{space_id}", type="primary")
    else:
        st.info("Genie space not yet configured. Run genie/create_genie_space.py.")
    st.markdown("**Example questions:**")
    for q in ["How many transactions have been successfully enriched?",
              "What percentage of transactions remain unmatched?",
              "Which payment facilitators generate the most ambiguous transactions?",
              "Which merchants have the highest transaction volumes?",
              "What is the overall merchant enrichment success rate?"]:
        st.markdown(f"- {q}")


def _current_user() -> str:
    import os
    return os.environ.get("DATABRICKS_CLIENT_ID", "analyst@databricks.com")


def main():
    _bootstrap()
    st.sidebar.title("🏦 Merchant Enrichment")
    st.sidebar.caption("Payments Operations · Databricks prototype")
    page = st.sidebar.radio("Navigate", ["Merchant Enrichment", "Operations Dashboard",
                                         "Manual Review", "Genie Analytics"])
    st.sidebar.divider()
    st.sidebar.caption(f"Catalog: `{CFG.catalog}`\n\nSchema: `{CFG.schema}`")
    if page == "Merchant Enrichment":
        section_enrichment()
    elif page == "Operations Dashboard":
        section_dashboard()
    elif page == "Manual Review":
        section_review()
    else:
        section_genie()


if __name__ == "__main__":
    main()
