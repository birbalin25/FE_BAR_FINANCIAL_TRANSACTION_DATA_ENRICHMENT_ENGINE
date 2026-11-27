# Speaker Narration — Financial Transaction Data Enrichment Engine
*Companion script to `pitch_deck.pdf`. Volume and cost figures are illustrative planning assumptions, not customer facts or industry benchmarks. Quality figures are measured prototype results on a 400-record held-out set.*

---

## SLIDE 1 — OPENING | ~1:00
Good morning, and thank you for your time.

I want to talk about a problem hidden inside everyday payment processing: knowing the actual merchant behind each card transaction.

A bank can process millions of card transactions a month, but the merchant information that arrives is often messy and inconsistent. The same coffee shop or retailer can show up under several different descriptions.

Our Financial Transaction Data Enrichment Engine turns those messy descriptors into trusted, standardized merchant identities. It combines generative AI, semantic search, governed data, and an analyst review step on the Databricks Data Intelligence Platform.

The goal is simple: cut avoidable manual investigations, prevent incorrect merchant attribution, and give operations and analytics reliable merchant data.

I'll cover the problem, the solution, the measured prototype results, and how we validate the value on your own data.

## SLIDE 2 — THE OUTCOME | ~1:05
Let me start with the outcome, not the technology.

In this illustrative operating model, the engine cuts manual investigation from about **4,000 analyst hours a month to about 940**.

That reclaims roughly **3,000 analyst hours every month** — about **36,700 hours a year**.

At an illustrative loaded rate of **$40 an hour**, that's about **$1.4M** in potential annual cost avoidance.

Just as important: on our held-out evaluation set, every automatic match was correct — a **0% false-positive rate**.

That's the point. We don't force a match on every transaction. We automate the clear cases and send uncertain ones to an analyst.

The volume and cost figures are planning assumptions, not your numbers. The quality metrics are measured prototype results, which I'll come to.

## SLIDE 3 — THE PROBLEM | ~1:05
Here's the problem in practice.

Take a transaction from Sunshine Coffee Roasters in Larchmont, New York. Depending on how it's processed, the bank might receive "SQ Sunshine Coffee Roasters Larchmont," "Square Sunshine Coffee Larchmont," or "Sunshine Coffee #1234 Larchmont NY."

To a person, these are clearly the same merchant. To downstream systems, they can look like different ones.

A descriptor may carry a facilitator prefix, an abbreviation, a store number, a location, a truncated name, or a misspelling — and sometimes the location is missing entirely.

When the merchant can't be identified reliably, the impact goes beyond messy data: merchant reporting fragments, disputes take longer, spend insights get inconsistent, and analysts investigate records that should resolve automatically.

The engine's job is to identify the merchant from the evidence — and to recognize when the evidence isn't enough for a safe decision.

## SLIDE 4 — COST OF THE STATUS QUO | ~1:05
Let's quantify the challenge using this business case.

Start with **10M** transactions a month. Assume **15%** have unclear descriptors — about **1.5M** transactions.

Assume **8%** of those need manual investigation — about **120,000** a month.

At about **2 minutes** each, that's **4,000 analyst hours** every month.

That's roughly **25 full-time analysts** identifying merchants from descriptions.

This isn't a claim that every bank looks like this. It's a transparent model showing how small percentages become a big operational burden at scale.

And manual effort grows with volume. The opportunity is to make resolution scalable without sacrificing data quality.

## SLIDE 5 — THE SOLUTION | ~1:30
The solution is a four-step workflow: understand, shortlist, decide, and serve and learn.

**First, understand.** A generative AI model reads the raw descriptor and pulls out structured attributes — likely merchant name, facilitator, city, state, and store number — separating the merchant from the surrounding text.

**Second, shortlist.** Databricks Vector Search retrieves the **10** most relevant candidates from the governed merchant master, using semantic similarity rather than exact string matching — so abbreviations and variations still match.

**Third, decide.** An LLM judge weighs the descriptor, the extracted attributes, and the candidates — name, aliases, and location — and returns one of three answers: matched, no match, or ambiguous.

That three-way decision is deliberate. If the evidence is weak, the engine doesn't guess; it sends the case to a human.

**Fourth, serve and learn.** The result is stored for operations, and analyst confirmations become reusable mappings — so a known descriptor skips the full AI workflow next time. That's also a cost saving: if a confirmed mapping exists, the engine returns it directly.

## SLIDE 6 — PROVEN RESULTS | ~1:25
Now the quality results.

We evaluated the prototype on **400** held-out transactions with known answers the engine never saw.

Matching precision was **100%** — every automatic match was correct — with a **0% false-positive rate**.

**Recall@10 was 99.2%**: for almost every matchable transaction, the correct merchant was in the 10 candidates from Vector Search. That matters, because the judge can't pick the right merchant if retrieval misses it.

Matching recall was **91.7%** — the share of matchable transactions resolved automatically.

No-match accuracy was **100%** on the unknown-merchant cases — the engine correctly declined to assign a merchant.

And **23.5%** of transactions were routed to manual review. That's by design: the goal is high-confidence automation with a controlled path for ambiguous cases — not 100% automation at any cost.

These are encouraging prototype metrics on a 400-record set, not a guarantee of production performance. A value proof of concept on your own descriptors is the way to confirm them at your scale.

## SLIDE 7 — QUANTIFIED IMPACT | ~1:10
Let's connect those quality results to the operating model.

Today, the assumptions give **4,000 analyst hours** a month. We apply the measured **23.5%** review rate to the **120,000** transactions that would otherwise need investigation.

That leaves about **28,200** for review — roughly **940 analyst hours** a month at 2 minutes each.

So the workload drops from **4,000 hours to about 940** — a reduction of about **3,060 hours a month**, or about **36,700 a year**.

At **$40** a loaded hour, that's about **$1.47M** a year, which we present as roughly **$1.4M** in illustrative annual cost avoidance.

Think of it as reclaimed capacity. Whether it becomes a budget cut depends on how the bank uses it — reducing overtime, absorbing growth without new hires, or moving analysts to higher-value work.

It's about **19 FTE** of freed capacity. You'd validate the real number with your own handling times, labor costs, and review patterns.

## SLIDE 8 — VALUE FOR BOTH SPONSORS | ~1:05
The value is different but complementary for your two sponsors.

For the **Chief Operating Officer**, it's operating efficiency: about **$1.4M** in annual cost avoidance, with capacity that scales through automation instead of headcount.

There's also risk. Wrong merchant attribution flows into disputes, fraud analysis, and reporting. The prototype's **0% false-positive rate** is a promising signal — production thresholds and monitoring would be validated on your data.

For the **Head of Payments Operations**, it's a smaller, more focused review queue. Analysts spend less time on routine cleanup and more on the genuinely hard cases.

They stay in control — reviewing, approving, or correcting — and confirmed mappings get reused.

And because the enriched data sits in governed tables with Genie, business users can ask questions in plain language — like which facilitators drive the most ambiguous descriptors — without writing SQL.

## SLIDE 9 — HOW IT WORKS ON DATABRICKS | ~1:10
The solution brings data, AI, operational serving, analytics, and the app together on one platform.

**Lakeflow** ingests and curates transaction and merchant data through Bronze, Silver, and Gold layers.

**Unity Catalog** provides governance and a documented source of truth.

The matching workflow combines **GenAI extraction, Vector Search retrieval, and the LLM judge** — with **MLflow** tracking model and prompt behavior and measuring quality against ground truth.

**Lakebase** is the operational store for results, reusable mappings, and the review queue.

A **Databricks App** gives the operations team one place to enrich, monitor, and review.

And **Genie** provides natural-language analytics over the governed Gold tables.

The benefit: these capabilities are connected on one platform, instead of scattered across unrelated tools.

## SLIDE 10 — WHERE WE ARE AND WHAT'S NEXT | ~1:10
This is a working end-to-end prototype, not just a diagram.

It has ingested and governed **8,000** transactions and **2,425** merchants. The enrichment workflow runs through extraction, Vector Search, and the judge.

The app is deployed, the analyst review loop works, Genie answers business questions on governed data, and quality is tracked in MLflow.

The next step is to validate the business case on a sample of your own descriptors.

We propose a **2-to-4-week** value proof of concept. First, agree on baseline metrics — descriptor volumes, current investigation rates, handling time, and your cost assumptions.

Then we evaluate against a labeled sample of your descriptors, measuring precision, Recall@10, false-positive rate, no-match accuracy, review rate, latency, and inference cost.

We tune confidence thresholds and facilitator coverage to your merchant mix. If results meet the agreed criteria, we plan live feeds, continuous enrichment, production governance, privacy controls, and monitoring.

That lets you validate both the quality and the economics before a broader rollout.

## SLIDE 11 — CLOSE | ~0:40
To close: the opportunity is to identify merchants more reliably, reclaim analyst capacity, and give the bank trusted merchant data.

The approach is practical — AI to read the descriptor, Vector Search to find likely merchants, an LLM judge to decide on the evidence, and human review when it's uncertain.

The illustrative case points to about **76%** less manual investigation and about **$1.4M** in annual cost avoidance. The prototype metrics are an encouraging start, with validation on your data as the next milestone.

Our ask is simple: sponsor a **2-to-4-week** value proof of concept on a representative sample of your descriptors, and agree on the measures that define success.

Identify every merchant with confidence. Reclaim your analysts. Trust the data behind your decisions.

Thank you.
