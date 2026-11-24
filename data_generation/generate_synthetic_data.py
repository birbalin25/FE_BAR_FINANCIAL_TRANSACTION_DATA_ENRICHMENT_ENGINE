"""Synthetic data generator for the Financial Transaction Enrichment Engine.

Generates four internally-consistent datasets with a fixed random seed:

  * merchants.csv        - canonical merchant reference (~2,500 records)
  * merchant_aliases.csv - alternative names mapped to merchant_id
  * transactions.csv     - raw card transactions with messy descriptors (~8,000)
  * ground_truth.csv     - expected mapping for an evaluation subset (~400)

NO real customer, Mastercard, or proprietary data is used. Everything is
procedurally generated from curated name pools.

The generator *knows* the true merchant behind every transaction, so it can
label each evaluation transaction as MATCHED / NO_MATCH / AMBIGUOUS. This label
lives ONLY in ground_truth.csv and is never exposed to the enrichment logic.

Usage:
    python data_generation/generate_synthetic_data.py [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import string
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic configuration (mirrors config/project_config.yaml defaults)
# ---------------------------------------------------------------------------
SEED = 42
N_MERCHANTS = 2500
N_TRANSACTIONS = 8000
N_EVAL = 400

# ---------------------------------------------------------------------------
# Curated pools
# ---------------------------------------------------------------------------
# (core_name, category, is_chain, website_domain)
BRANDS = [
    ("Sunshine Coffee Roasters", "Coffee Shop", True, "sunshinecoffee.com"),
    ("Bluebird Cafe", "Coffee Shop", True, "bluebirdcafe.com"),
    ("Morning Brew Coffee", "Coffee Shop", True, "morningbrew.coffee"),
    ("Daily Grind Coffee", "Coffee Shop", True, "dailygrind.coffee"),
    ("Riverside Roasters", "Coffee Shop", False, "riversideroasters.com"),
    ("Taco Fiesta", "Restaurant", True, "tacofiesta.com"),
    ("Golden Dragon Chinese", "Restaurant", True, "goldendragon.com"),
    ("Bella Napoli Pizzeria", "Restaurant", True, "bellanapoli.com"),
    ("The Burger Joint", "Restaurant", True, "burgerjoint.com"),
    ("Green Leaf Salads", "Restaurant", True, "greenleaf.com"),
    ("Smokehouse BBQ", "Restaurant", True, "smokehousebbq.com"),
    ("Noodle House", "Restaurant", True, "noodlehouse.com"),
    ("Fresh Market Grocers", "Grocery", True, "freshmarket.com"),
    ("Green Valley Foods", "Grocery", True, "greenvalleyfoods.com"),
    ("Cornerstone Market", "Grocery", True, "cornerstonemkt.com"),
    ("Harvest Foods", "Grocery", True, "harvestfoods.com"),
    ("QuickFuel Gas", "Gas Station", True, "quickfuel.com"),
    ("Speedway Mart", "Convenience Store", True, "speedwaymart.com"),
    ("Corner Pantry", "Convenience Store", True, "cornerpantry.com"),
    ("Urban Threads", "Apparel", True, "urbanthreads.com"),
    ("Denim and Co", "Apparel", True, "denimandco.com"),
    ("Trailhead Outfitters", "Apparel", True, "trailhead.com"),
    ("Cozy Home Goods", "Home Goods", True, "cozyhome.com"),
    ("TechNova Electronics", "Electronics", True, "technova.com"),
    ("GadgetWorld", "Electronics", True, "gadgetworld.com"),
    ("Wellness Pharmacy", "Pharmacy", True, "wellnessrx.com"),
    ("CarePoint Drugs", "Pharmacy", True, "carepoint.com"),
    ("Blue Ridge Hardware", "Home Improvement", True, "blueridgehw.com"),
    ("Builders Depot", "Home Improvement", True, "buildersdepot.com"),
    ("GreenThumb Garden", "Home Improvement", False, "greenthumb.com"),
    ("Luxe Salon and Spa", "Beauty", True, "luxesalon.com"),
    ("Shear Elegance", "Beauty", False, "shearelegance.com"),
    ("PeakFit Gym", "Fitness", True, "peakfit.com"),
    ("IronWorks Fitness", "Fitness", True, "ironworks.fitness"),
    ("CloudStream Media", "Digital Services", True, "cloudstream.com"),
    ("PixelForge Studios", "Digital Services", True, "pixelforge.io"),
    ("BrightLearn Academy", "Education", True, "brightlearn.com"),
    ("Sweet Crumbs Bakery", "Bakery", True, "sweetcrumbs.com"),
    ("Flour Power Bakery", "Bakery", False, "flourpower.com"),
    ("Happy Paws Pet Supplies", "Pet Store", True, "happypaws.com"),
    ("AutoCare Service Center", "Automotive", True, "autocare.com"),
    ("Precision Auto Parts", "Automotive", True, "precisionauto.com"),
    ("Chapter One Books", "Retail", True, "chapterone.com"),
    ("Petals and Stems Florist", "Florist", False, "petalsandstems.com"),
    ("Hoppy Trails Brewing", "Bar", True, "hoppytrails.com"),
    ("Cask and Barrel Tavern", "Bar", False, "caskandbarrel.com"),
    ("Metro Dry Cleaners", "Services", True, "metrodrycleaners.com"),
    ("Sparkle Car Wash", "Services", True, "sparklecarwash.com"),
    ("City Dental Care", "Healthcare", True, "citydental.com"),
    ("Lakeside Veterinary", "Healthcare", False, "lakesidevet.com"),
]

CITIES = [
    ("Larchmont", "NY", "10538"), ("Brooklyn", "NY", "11201"), ("Austin", "TX", "78701"),
    ("Dallas", "TX", "75201"), ("Chicago", "IL", "60601"), ("Naperville", "IL", "60540"),
    ("Seattle", "WA", "98101"), ("Bellevue", "WA", "98004"), ("Portland", "OR", "97201"),
    ("San Jose", "CA", "95110"), ("Oakland", "CA", "94607"), ("Pasadena", "CA", "91101"),
    ("Denver", "CO", "80202"), ("Boulder", "CO", "80301"), ("Boston", "MA", "02108"),
    ("Cambridge", "MA", "02139"), ("Miami", "FL", "33101"), ("Orlando", "FL", "32801"),
    ("Atlanta", "GA", "30303"), ("Savannah", "GA", "31401"), ("Nashville", "TN", "37201"),
    ("Memphis", "TN", "38103"), ("Phoenix", "AZ", "85004"), ("Tucson", "AZ", "85701"),
    ("Charlotte", "NC", "28202"), ("Raleigh", "NC", "27601"), ("Columbus", "OH", "43215"),
    ("Cleveland", "OH", "44113"), ("Minneapolis", "MN", "55401"), ("Madison", "WI", "53703"),
    ("Philadelphia", "PA", "19103"), ("Pittsburgh", "PA", "15222"), ("Richmond", "VA", "23219"),
    ("Arlington", "VA", "22201"), ("Houston", "TX", "77002"), ("San Diego", "CA", "92101"),
    ("Sacramento", "CA", "95814"), ("Salt Lake City", "UT", "84101"), ("Las Vegas", "NV", "89101"),
    ("Kansas City", "MO", "64106"), ("St Louis", "MO", "63101"), ("Detroit", "MI", "48226"),
]

STREETS = ["Main St", "Oak Ave", "Maple Dr", "Washington Blvd", "Market St", "Elm St",
           "Park Ave", "Cedar Ln", "Lincoln Rd", "Broadway", "Highland Ave", "Lake St"]

# Payment facilitators: canonical label -> list of raw descriptor prefixes
FACILITATORS = {
    "Square": ["SQ *", "SQ*", "SQUARE *", "SQ •"],
    "PayPal": ["PAYPAL *", "PP*", "PAYPAL •", "PYPL *"],
    "Stripe": ["STRIPE", "STRIPE*", "STR*"],
    "Toast": ["TST*", "TST* "],
    "Clover": ["CLV*", "CLOVER *"],
    "Venmo": ["VENMO *", "VEN*"],
}
# Fraction of merchants that route through a facilitator at all
FACILITATOR_CATEGORIES = {"Coffee Shop", "Restaurant", "Bakery", "Beauty", "Bar",
                          "Digital Services", "Services", "Florist", "Fitness"}

random.seed(SEED)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Merchant:
    merchant_id: str
    merchant_name: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str
    merchant_category: str
    website: str
    phone_number: str
    _brand: str          # internal, not written to CSV
    _is_chain: bool      # internal


@dataclass
class Alias:
    alias_id: str
    merchant_id: str
    alias_name: str
    alias_type: str


@dataclass
class Transaction:
    transaction_id: str
    transaction_date: str
    transaction_amount: float
    currency: str
    raw_transaction_descriptor: str
    country: str
    payment_facilitator: str   # raw hint only; may be "" / unknown


@dataclass
class GroundTruth:
    transaction_id: str
    expected_decision: str          # MATCHED / NO_MATCH / AMBIGUOUS
    expected_merchant_id: str       # "" when not a single match
    expected_merchant_name: str
    expected_payment_facilitator: str
    expected_city: str
    expected_state: str


# ---------------------------------------------------------------------------
# Name-mangling helpers (produce messy descriptors)
# ---------------------------------------------------------------------------
def _abbreviate(name: str) -> str:
    words = name.split()
    out = []
    for w in words:
        r = random.random()
        if len(w) > 5 and r < 0.4:
            out.append(w[: random.randint(3, 5)])
        elif w.lower() in ("and",) and r < 0.7:
            continue
        else:
            out.append(w)
    return " ".join(out)


def _misspell(name: str) -> str:
    if len(name) < 4:
        return name
    chars = list(name)
    op = random.choice(["drop", "swap", "double"])
    i = random.randint(0, len(chars) - 2)
    if chars[i] == " " or chars[i + 1] == " ":
        return name
    if op == "drop":
        del chars[i]
    elif op == "swap":
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    else:
        chars.insert(i, chars[i])
    return "".join(chars)


def _truncate(name: str) -> str:
    n = random.randint(max(6, len(name) // 2), len(name))
    return name[:n].rstrip()


def _store_num() -> str:
    style = random.choice(["#", "STORE ", "", "ST#", "LOC "])
    return f"{style}{random.randint(1, 9999):04d}" if style else f"{random.randint(1, 999)}"


def _order_id() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(6, 10)))


# ---------------------------------------------------------------------------
# Build merchants
# ---------------------------------------------------------------------------
def build_merchants() -> list[Merchant]:
    merchants: list[Merchant] = []
    mid = 1
    # Assign per-brand location counts to roughly hit N_MERCHANTS
    chain_brands = [b for b in BRANDS if b[2]]
    unique_brands = [b for b in BRANDS if not b[2]]
    remaining = N_MERCHANTS - len(unique_brands)
    per_chain = max(10, remaining // max(1, len(chain_brands)))

    for core, cat, is_chain, domain in BRANDS:
        n_loc = 1 if not is_chain else random.randint(int(per_chain * 0.5), int(per_chain * 1.5))
        chosen = random.sample(CITIES, min(n_loc, len(CITIES)))
        # if we need more locations than distinct cities, allow repeats with suffixes
        while len(chosen) < n_loc:
            chosen.append(random.choice(CITIES))
        for city, state, postal in chosen:
            if len(merchants) >= N_MERCHANTS:
                break
            addr = f"{random.randint(1, 9999)} {random.choice(STREETS)}"
            phone = f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
            merchants.append(Merchant(
                merchant_id=f"M{mid:05d}",
                merchant_name=core,
                address=addr,
                city=city,
                state=state,
                country="USA",
                postal_code=postal,
                merchant_category=cat,
                website=f"https://www.{domain}",
                phone_number=phone,
                _brand=core,
                _is_chain=is_chain,
            ))
            mid += 1
        if len(merchants) >= N_MERCHANTS:
            break
    return merchants


# ---------------------------------------------------------------------------
# Build aliases
# ---------------------------------------------------------------------------
def _short_name(name: str) -> str:
    """Drop filler words ('and'/'the') and keep the first 1-2 salient words."""
    words = [w for w in name.split() if w.lower() not in ("and", "the", "co")]
    return " ".join(words[:2]) if len(words) > 2 else " ".join(words)


def build_aliases(merchants: list[Merchant]) -> list[Alias]:
    aliases: list[Alias] = []
    aid = 1
    seen_brand: set[str] = set()
    for m in merchants:
        emitted: set[str] = set()

        def _emit(alias_name: str, atype: str):
            nonlocal aid
            alias_name = alias_name.strip()
            key = alias_name.lower()
            if not alias_name or key in emitted or key == m.merchant_name.lower():
                return
            emitted.add(key)
            aliases.append(Alias(f"A{aid:06d}", m.merchant_id, alias_name, atype))
            aid += 1

        # Per-merchant variants (guaranteed-useful alternatives to the canonical name)
        _emit(_short_name(m.merchant_name), "short_name")
        _emit(_abbreviate(m.merchant_name), "abbreviation")
        if random.random() < 0.5:
            _emit(_misspell(m.merchant_name).title(), "misspelling")
        # a POS-style facilitator-prefixed form for facilitator-heavy categories
        if m.merchant_category in FACILITATOR_CATEGORIES:
            fac = random.choice(list(FACILITATORS.keys()))
            prefix = FACILITATORS[fac][0]
            _emit(f"{prefix}{_short_name(m.merchant_name).upper()}", "facilitator_prefixed")

        # Brand-level legal / dba names (once per brand)
        if m._brand not in seen_brand:
            seen_brand.add(m._brand)
            _emit(f"{m.merchant_name} LLC", "legal_name")
            _emit(f"{m.merchant_name.split()[0].upper()} GROUP", "dba")
    return aliases


# ---------------------------------------------------------------------------
# Build a raw descriptor for a given merchant
# ---------------------------------------------------------------------------
def make_descriptor(m: Merchant, include_location: bool, use_facilitator: bool):
    """Return (descriptor, facilitator_label, facilitator_canonical)."""
    name = m.merchant_name
    # name mangling
    style = random.random()
    if style < 0.30:
        disp = _abbreviate(name)
    elif style < 0.45:
        disp = _misspell(name)
    elif style < 0.55:
        disp = _truncate(name)
    else:
        disp = name
    disp = disp.upper()

    parts = []
    facilitator_label = ""
    facilitator_canonical = "UNKNOWN"
    if use_facilitator:
        facilitator_canonical = random.choice(list(FACILITATORS.keys()))
        facilitator_label = random.choice(FACILITATORS[facilitator_canonical])
        parts.append(f"{facilitator_label}{disp}" if facilitator_label.endswith("*")
                     or facilitator_label.endswith(" ") else f"{facilitator_label}{disp}")
    else:
        parts.append(disp)

    # optional store number
    if random.random() < 0.35:
        parts.append(_store_num())

    # optional location
    if include_location:
        if random.random() < 0.5:
            parts.append(f"{m.city.upper()} {m.state}")
        else:
            parts.append(f"{m.city.upper()}")

    # optional order id / extra noise
    if random.random() < 0.20:
        parts.append(_order_id())

    # punctuation / formatting noise
    sep = random.choice([" ", "  ", " * ", " / ", " - "])
    descriptor = sep.join(parts)
    if random.random() < 0.15:
        descriptor = descriptor.replace(" ", "")  # jammed-together tokens
    return descriptor.strip(), facilitator_canonical


def make_unknown_descriptor():
    """A descriptor that refers to no merchant in our reference data."""
    unknown_cores = ["QUANTUM WIDGETS", "ZEPHYR SUPPLY CO", "ACME UNLISTED LLC",
                     "GLOBEX TRADING", "NOVA UNKNOWN MERCHANT", "XYZ ENTERPRISES",
                     "MYSTERY VENDOR 774", "UNIDENTIFIED POS TXN", "INITECH SERVICES"]
    core = random.choice(unknown_cores)
    parts = [core]
    if random.random() < 0.5:
        city, state, _ = random.choice(CITIES)
        parts.append(f"{city.upper()} {state}")
    if random.random() < 0.4:
        parts.append(_order_id())
    return " ".join(parts), random.choice(["UNKNOWN", "Square", "Stripe"])


# ---------------------------------------------------------------------------
# Build transactions + ground truth
# ---------------------------------------------------------------------------
def build_transactions(merchants: list[Merchant]):
    # index brand -> merchant records (to detect ambiguity)
    brand_to_merchants: dict[str, list[Merchant]] = {}
    for m in merchants:
        brand_to_merchants.setdefault(m._brand, []).append(m)

    chain_brands = [b for b, ms in brand_to_merchants.items() if len(ms) > 1]

    txns: list[Transaction] = []
    truths: list[GroundTruth] = []

    start = datetime(2025, 8, 1)
    # popularity weights: favor chains
    weights = [5 if m._is_chain else 1 for m in merchants]

    for i in range(1, N_TRANSACTIONS + 1):
        tid = f"T{i:06d}"
        date = (start + timedelta(days=random.randint(0, 90),
                                  seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S")
        amount = round(random.uniform(2.5, 850.0), 2)
        roll = random.random()

        if roll < 0.08:
            # ---- NO_MATCH: unknown merchant ----
            desc, fac = make_unknown_descriptor()
            txns.append(Transaction(tid, date, amount, "USD", desc, "USA", fac))
            truths.append(GroundTruth(tid, "NO_MATCH", "", "", fac, "", ""))
            continue

        m = random.choices(merchants, weights=weights, k=1)[0]
        use_fac = m.merchant_category in FACILITATOR_CATEGORIES and random.random() < 0.6
        is_chain_brand = m._brand in chain_brands

        if roll < 0.20 and is_chain_brand:
            # ---- AMBIGUOUS: chain name, NO location -> many candidate stores ----
            desc, fac = make_descriptor(m, include_location=False, use_facilitator=use_fac)
            txns.append(Transaction(tid, date, amount, "USD", desc, "USA", fac))
            truths.append(GroundTruth(tid, "AMBIGUOUS", "", m.merchant_name,
                                      fac, "", ""))
        else:
            # ---- MATCHED: include location (or unique brand) ----
            include_loc = True if is_chain_brand else random.random() < 0.7
            desc, fac = make_descriptor(m, include_location=include_loc, use_facilitator=use_fac)
            txns.append(Transaction(tid, date, amount, "USD", desc, "USA", fac))
            truths.append(GroundTruth(tid, "MATCHED", m.merchant_id, m.merchant_name,
                                      fac, m.city, m.state))
    return txns, truths


# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(path: Path, rows, fields):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            d = asdict(r) if hasattr(r, "__dataclass_fields__") else r
            w.writerow({k: d[k] for k in fields})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "output"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[seed={SEED}] generating merchants...")
    merchants = build_merchants()
    print(f"  -> {len(merchants)} merchants")

    aliases = build_aliases(merchants)
    print(f"  -> {len(aliases)} aliases")

    txns, truths = build_transactions(merchants)
    print(f"  -> {len(txns)} transactions")

    # ground-truth evaluation subset: sample across all three decision types
    by_decision: dict[str, list[GroundTruth]] = {}
    for t in truths:
        by_decision.setdefault(t.expected_decision, []).append(t)
    eval_rows: list[GroundTruth] = []
    # proportional-ish stratified sample
    quota = {"MATCHED": int(N_EVAL * 0.6), "AMBIGUOUS": int(N_EVAL * 0.2),
             "NO_MATCH": int(N_EVAL * 0.2)}
    for dec, q in quota.items():
        pool = by_decision.get(dec, [])
        eval_rows.extend(random.sample(pool, min(q, len(pool))))
    random.shuffle(eval_rows)

    merchant_fields = ["merchant_id", "merchant_name", "address", "city", "state",
                       "country", "postal_code", "merchant_category", "website", "phone_number"]
    write_csv(out / "merchants.csv", merchants, merchant_fields)
    write_csv(out / "merchant_aliases.csv", aliases,
              ["alias_id", "merchant_id", "alias_name", "alias_type"])
    write_csv(out / "transactions.csv", txns,
              ["transaction_id", "transaction_date", "transaction_amount", "currency",
               "raw_transaction_descriptor", "country", "payment_facilitator"])
    write_csv(out / "ground_truth.csv", eval_rows,
              ["transaction_id", "expected_decision", "expected_merchant_id",
               "expected_merchant_name", "expected_payment_facilitator",
               "expected_city", "expected_state"])

    # summary + sample evidence
    dist = {k: len(v) for k, v in by_decision.items()}
    eval_dist: dict[str, int] = {}
    for r in eval_rows:
        eval_dist[r.expected_decision] = eval_dist.get(r.expected_decision, 0) + 1
    summary = {
        "seed": SEED,
        "merchants": len(merchants),
        "distinct_brands": len({m._brand for m in merchants}),
        "aliases": len(aliases),
        "transactions": len(txns),
        "transaction_decision_distribution": dist,
        "ground_truth_rows": len(eval_rows),
        "ground_truth_distribution": eval_dist,
        "sample_descriptors": [t.raw_transaction_descriptor for t in txns[:15]],
    }
    with open(out / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote CSVs + summary.json to {out}")


if __name__ == "__main__":
    main()
