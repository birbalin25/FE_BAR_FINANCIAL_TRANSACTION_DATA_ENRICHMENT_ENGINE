# Financial Transaction Data Enrichment Engine
### Pitch deck — business audience
**Industry:** Banking & Financial Services · Card Issuing · **Audience:** Chief Operating Officer (executive sponsor) & Head of Payments Operations (domain owner)

> Text-readable companion to `pitch_deck.pdf`. Volume & cost figures are **illustrative planning assumptions**; quality figures are **measured** on a held-out evaluation set of 400 transactions.

---

## Slide 1 — Title
**Financial Transaction Data Enrichment Engine**
Turn millions of messy card-transaction descriptors into **trusted, standardized merchant identities** — automatically, and with zero false matches.
Built on the Databricks Data Intelligence Platform · Working prototype.

---

## Slide 2 — The business outcome (lead)
**Reclaim ~3,000 analyst hours a month — and stop mis-identifying merchants.**
An AI engine identifies the real merchant behind each transaction, auto-resolving the cases your team investigates by hand today and routing only the genuinely ambiguous ones to analysts.

| ~76% | ~3,000 hrs | 0% | ~$1.4M |
|---|---|---|---|
| fewer manual investigations | analyst time reclaimed / month | false-match rate on auto-decisions | annual operating-cost avoidance |

---

## Slide 3 — The problem
**The same merchant arrives looking like four different ones.**
```
SQ *SUNSHINE COFFEE ROASTERS LARCHMONT NY
SQUARE SUNSHINE COFFEE LARCHMONT
SQ SUNSHINE COFFEE ROASTERS
SUNSHINE COFFEE #1234 LARCHMONT NY
```
→ all one merchant: **Sunshine Coffee Roasters, Larchmont NY**.
Facilitator prefixes, abbreviations, misspellings, truncation, store numbers, and missing locations make the merchant unidentifiable. When the bank can't reliably name the merchant, it can't resolve disputes quickly, detect fraud accurately, or give clean spend data — so people investigate by hand.

---

## Slide 4 — Cost of the status quo
**Manual investigation doesn't scale with transaction volume.** (Illustrative assumptions)
- **10M** card transactions / month
- **15%** have inconsistent/unclear descriptors → 1.5M
- **8%** of those require manual investigation → **120,000 / month**
- @ ~2 min each → **~4,000 analyst hours / month ≈ 25 full-time analysts**

Effort grows directly with volume and produces no customer value when done manually.

---

## Slide 5 — The solution
**AI that identifies the merchant — and knows when to ask a human.**
1. **Understand** — GenAI reads the raw descriptor and separates facilitator, merchant name, location & store number.
2. **Shortlist** — Vector search retrieves the 10 most similar merchants from the governed merchant master.
3. **Decide** — an LLM judge weighs name *and* location → **MATCHED / NO_MATCH / AMBIGUOUS**.
4. **Serve & learn** — results stored analytics-ready; analyst confirmations become reusable mappings (instant, no AI spend on repeats).

**Guardrail by design:** the engine never forces a match. Uncertain cases go to review — protecting you from wrong merchant attributions.

---

## Slide 6 — Proven results (measured on 400 held-out transactions)
| Metric | Value | Meaning |
|---|---|---|
| Matching precision | **100%** | every auto-match was correct |
| False-positive rate | **0%** | the key risk metric |
| Recall@10 | **99.2%** | right merchant is in the shortlist |
| Matching recall | **91.7%** | of matchable transactions resolved |
| "No-match" accuracy | **100%** | unknown merchants flagged, not guessed |
| Routed to manual review | **23.5%** | only the genuinely ambiguous |

---

## Slide 7 — Quantified impact
**From 4,000 manual hours a month to under 1,000.**
Applying the measured 23.5% review rate to the 120k currently-manual transactions:
- Manual hours/month: **4,000 → ~940**
- **~3,000 hours reclaimed every month** (~36,700 / year)
- **~19 FTE** of analyst capacity freed for higher-value work
- **~$1.4M** illustrative annual cost avoidance @ ~$40/loaded hour

---

## Slide 8 — Value for both decision-makers
**Chief Operating Officer (executive sponsor)**
- **Operating cost down:** ~$1.4M/yr avoided; capacity scales with AI, not headcount.
- **Risk down:** 0% false-match rate → fewer wrong merchant attributions feeding fraud, disputes & regulatory reporting.
- **Governed & auditable:** every decision stored with its reason on Unity Catalog.
- **Fast to value:** working end-to-end prototype on one platform in hours.

**Head of Payments Operations (domain owner)**
- **Smaller, cleaner queue:** ~76% of manual cases auto-resolved; analysts see only the hard ones.
- **Analysts in control:** review/approve/correct; the engine learns, so the same descriptor is never investigated twice.
- **Self-service answers:** ask in plain English ("Which facilitators cause the most ambiguity?") — no SQL, no tickets.
- **Confidence to act:** standardized merchant data for disputes, chargebacks & customer statements.

---

## Slide 9 — How it works (one platform)
Lakeflow (ingest/curate) → Unity Catalog (govern) → GenAI + Vector Search + MLflow (match & measure) → Lakebase (operational serving) → Databricks App (ops workplace) + Genie (NL analytics).
No data movement, no stitched-together tools — data, AI, serving, analytics and the app on one governed platform.

---

## Slide 10 — Where we are / what's next
**Live today (prototype):** 8,000 transactions & 2,425 merchants ingested & governed; enrichment running; app deployed with analyst review loop; Genie answering real questions; quality tracked in MLflow.
**Path to production:** value POC on your real descriptors → connect the live card feed & schedule enrichment → tune thresholds & facilitator coverage → scale vector search → production governance, PII masking & monitoring.
**Proposed next step:** a **2–4 week value POC on your data** to confirm hours saved and the false-positive rate in your environment.

---

## Slide 11 — The bottom line
**Identify every merchant automatically. Reclaim your analysts. Trust every match.**
~76% less manual work · 0% false matches · ~$1.4M annual savings (illustrative) · 1 governed platform.
