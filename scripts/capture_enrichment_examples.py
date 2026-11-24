"""Capture detailed, real enrichment examples (MATCHED / NO_MATCH / AMBIGUOUS)
into evidence/enrichment_examples.md by running the live workflow on actual
transactions and comparing to held-out ground truth.
"""
from __future__ import annotations

from common.config import CFG
from common.dbx import rows
from common.enrichment_service import enrich
from common.evidence import header, md_table

T = CFG.catalog + "." + CFG.schema


def sample(decision: str, n: int) -> list[dict]:
    return rows(f"""
        SELECT g.transaction_id, t.raw_transaction_descriptor AS descriptor,
               g.expected_decision, g.expected_merchant_id, g.expected_merchant_name,
               g.expected_city, g.expected_state
        FROM {T}.eval_ground_truth g
        JOIN {T}.gold_transactions t USING (transaction_id)
        WHERE g.expected_decision = '{decision}'
        ORDER BY g.transaction_id
        LIMIT {n}
    """)


def main():
    picks = sample("MATCHED", 5) + sample("AMBIGUOUS", 4) + sample("NO_MATCH", 3)
    parts = [header("Phase 2 Evidence — GenAI Entity Recognition, Vector Search & LLM Judge",
                    "Live end-to-end enrichment output on real transactions. Models: chat "
                    f"`{CFG.models['chat_endpoint']}`, embeddings `{CFG.models['embedding_endpoint']}`. "
                    "Ground-truth `expected_*` columns are shown ONLY for verification and are never "
                    "seen by the enrichment workflow.")]

    agree = 0
    for i, row in enumerate(picks, 1):
        desc = row["descriptor"]
        r = enrich(desc)
        ent = r["extracted_entities"] or {}
        exp_dec = row["expected_decision"]
        got_dec = r["decision"]
        match_flag = "✅" if got_dec == exp_dec else "⚠️"
        if got_dec == exp_dec:
            agree += 1

        parts.append(f"\n---\n\n## Example {i} — expected **{exp_dec}**, system decided "
                     f"**{got_dec}** {match_flag}\n")
        parts.append(f"**Transaction** `{row['transaction_id']}`  \n")
        parts.append(f"**Raw descriptor:** `{desc}`\n")

        parts.append("\n**1) Extracted entities (GenAI):**\n")
        parts.append(md_table([{
            "payment_facilitator": ent.get("payment_facilitator"),
            "merchant_name": ent.get("merchant_name"),
            "city": ent.get("city"), "state": ent.get("state"),
            "store_identifier": ent.get("store_identifier"),
            "order_identifier": ent.get("order_identifier"),
        }]))

        parts.append("\n**2) Vector Search — top candidates (similarity):**\n")
        cand_rows = [{
            "similarity": c["similarity_score"], "merchant_id": c["merchant_id"],
            "merchant_name": c["merchant_name"], "city": c["city"], "state": c["state"],
            "category": c["merchant_category"],
        } for c in r["candidates"][:10]]
        parts.append(md_table(cand_rows))

        parts.append("\n**3) LLM judge decision:**\n")
        parts.append(md_table([{
            "decision": r["decision"], "merchant_id": r["merchant_id"],
            "merchant_name": r["merchant_name"], "confidence": r["confidence"],
            "alternatives": ", ".join(r["alternative_candidates"]) or "—",
        }]))
        parts.append(f"\n> **Reason:** {r['reason']}\n")
        parts.append(f"\n_Latency: {r['latency_ms']} ms · LLM calls: {r['llm_calls']} · "
                     f"Ground truth: {exp_dec}"
                     + (f" / merchant {row['expected_merchant_id']}" if row['expected_merchant_id'] else "")
                     + "_\n")

    parts.insert(1, f"\n**Summary:** {agree}/{len(picks)} examples agreed with ground-truth "
                    f"decision on this curated sample. Full quantitative evaluation over all 400 "
                    f"held-out transactions is in [`evaluation_results.md`](evaluation_results.md).\n")

    with open("evidence/enrichment_examples.md", "w") as f:
        f.write("\n".join(parts))
    print(f"wrote evidence/enrichment_examples.md ({agree}/{len(picks)} agreed)")


if __name__ == "__main__":
    main()
