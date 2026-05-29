"""
Synthetic CRM accounts dataset for NIS2 classification demo.

Generates ~7,500 fake B2B SaaS accounts with realistic distributions across:
- NIS2-relevant industries (Energy, Health, Finance, Manufacturing, etc.)
- Out-of-scope industries (Construction, Trade, Hotels, etc.)
- Account types (Customer, Customer Churning, Prospect, etc.)
- Customer lifecycle status (active, non_renewing, cancelled, etc.)
- A primary industry field (~80% populated) and a secondary cleaned field (~38% populated)

Deterministic: uses a fixed seed so the output is identical across runs.
Output: data/synthetic_accounts.csv

Usage:
    python data/generate_synthetic_data.py
"""

from __future__ import annotations

import csv
import random
import uuid
from pathlib import Path

try:
    from faker import Faker
except ImportError:
    raise SystemExit("Faker is required. Install with: pip install faker")

# ---------------------------------------------------------------------
# Configuration — tweak these to change dataset characteristics
# ---------------------------------------------------------------------
SEED = 42
TOTAL_ACCOUNTS = 7500
OUTPUT_PATH = Path(__file__).parent / "synthetic_accounts.csv"

# Industry distribution — weighted to reflect a B2B fleet/SaaS customer base.
# Mix of NIS2-relevant sectors (Energy, Health, Finance) and out-of-scope
# sectors (Construction, Trade, Hotels). Roughly matches the shape an EU
# SME-focused B2B SaaS would actually see.
INDUSTRY_WEIGHTS = {
    # ===== OUT OF SCOPE (the bulk of the base) =====
    "Construction and Engineering": 950,
    "Service Industry": 440,
    "Trade": 300,
    "Property and Housing Sector": 230,
    "Consultancies and Agencies": 230,
    "Hotels and Gastronomy": 180,
    "Education and Teaching": 110,
    "Tax Advisors": 100,
    "Heating/Sanitary": 90,
    "Electrical Installation": 80,
    "Advertising and Marketing": 70,
    "Arts and Entertainment": 60,
    "Agriculture and Forestry": 50,
    "Publishing": 25,

    # ===== ESSENTIAL ENTITY (NIS2 Annex 1) =====
    "Energy Industry": 110,
    "Health Care and Social Sector": 420,
    "Medical Technology": 65,
    "Finance and Insurance Services": 215,
    "Telecommunications Sector": 45,

    # ===== IMPORTANT ENTITY (NIS2 Annex 2) =====
    "Manufacturing and Processing": 340,
    "Food Manufacturing and Processing": 115,
    "Chemical Industry": 30,
    "Automotive Industry": 140,
    "Transportation": 120,
    "Logistics Sector": 120,

    # ===== MIXED / NEEDS REVIEW =====
    "IT Service": 260,
    "Public Administration": 50,

    # ===== UNKNOWN / NULL VARIANTS =====
    "Others": 180,
    "Unknown": 25,
    "Industry not matched": 15,
    "Not matched": 8,
    "Industrial Services": 2,
}

# Account type distribution (mirrors the real-world pattern where most
# active records are true Customers, with smaller pools of churning/lost/prospect)
ACCOUNT_TYPE_WEIGHTS = {
    "Customer":              6550,
    "Customer Churning":      620,
    "Customer Lost":           65,
    "Customer Lost Legacy":    45,
    "Prospect":               210,
    "Prosumer":                10,
}

# Customer lifecycle status (DWH-style) — most active customers are billing,
# some are non-renewing, some are cancelled, prospects/leads are null
STATUS_WEIGHTS = {
    "active":        6657,
    "cancelled":      450,
    "non_renewing":   634,
    "future":           2,
    "trial":            1,
}

# Realistic ARR distribution: heavy long-tail SMB book with a few large accounts.
# Median around €600, p95 around €4k, max ~€100k
def synthetic_arr(rng: random.Random) -> float:
    """Long-tailed ARR — log-normal-ish."""
    base = rng.lognormvariate(mu=6.4, sigma=1.1)   # mean ~€900, median ~€600
    # cap extreme outliers but allow a few enterprise-sized accounts
    return round(min(base, 100000), 2)


# Country distribution biased toward EU/DACH (matches a Berlin-based B2B SaaS)
COUNTRY_WEIGHTS = {
    "Germany":        4200,
    "Austria":         500,
    "Switzerland":     420,
    "Netherlands":     350,
    "Poland":          280,
    "France":          250,
    "Spain":           230,
    "Italy":           200,
    "Belgium":         180,
    "Czech Republic":  150,
    "United Kingdom":  140,
    "Denmark":         110,
    "Sweden":           90,
    "Portugal":         70,
    "Ireland":          60,
    "Other EU":         50,
}

CURRENCY_BY_COUNTRY = {
    "Germany": "EUR", "Austria": "EUR", "Netherlands": "EUR", "France": "EUR",
    "Spain": "EUR", "Italy": "EUR", "Belgium": "EUR", "Portugal": "EUR",
    "Ireland": "EUR", "Other EU": "EUR",
    "Switzerland": "CHF",
    "Poland": "PLN",
    "Czech Republic": "CZK",
    "Denmark": "DKK",
    "Sweden": "SEK",
    "United Kingdom": "GBP",
}


# ---------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------
def weighted_choice(rng: random.Random, weights: dict[str, int]) -> str:
    keys = list(weights.keys())
    vals = list(weights.values())
    return rng.choices(keys, weights=vals, k=1)[0]


def fake_company_name(fake: Faker, country: str) -> str:
    """Generate a country-flavoured company name."""
    base = fake.company()
    suffix_map = {
        "Germany":        ["GmbH", "AG", "GmbH & Co. KG", "SE"],
        "Austria":        ["GmbH", "AG"],
        "Switzerland":    ["AG", "GmbH", "SA"],
        "Netherlands":    ["B.V.", "N.V."],
        "France":         ["SAS", "SARL", "SA"],
        "Spain":          ["S.L.", "S.A."],
        "Italy":          ["S.r.l.", "S.p.A."],
        "Poland":         ["Sp. z o.o.", "S.A."],
        "Belgium":        ["BV", "NV"],
        "United Kingdom": ["Ltd", "Limited", "plc"],
        "Sweden":         ["AB"],
        "Denmark":        ["A/S", "ApS"],
    }
    suffixes = suffix_map.get(country, ["Ltd"])
    # Remove existing suffix if Faker added one
    for s in ("Inc", "LLC", "Group", "and Sons", "and Co"):
        base = base.replace(f", {s}", "").replace(f" {s}", "")
    return f"{base} {fake.random_element(suffixes)}"


def generate_industry_pair(rng: random.Random) -> tuple[str | None, str | None]:
    """
    Generate (primary_industry, secondary_industry_sector) with realistic
    fill rates and partial agreement.

    - Primary ('industry') field is populated ~80% of the time.
    - Secondary ('industry_sector') is a cleaned/consolidated version
      populated ~75% of the time, with some 'Others' bucketing.
    - The two agree most of the time but the secondary occasionally
      consolidates specific industries into 'Others'.
    """
    has_primary = rng.random() < 0.81
    has_secondary = rng.random() < 0.75

    primary = weighted_choice(rng, INDUSTRY_WEIGHTS) if has_primary else None

    if not has_secondary:
        secondary = None
    elif primary is None:
        # Sometimes only secondary is populated (lead conversions, etc.)
        secondary = weighted_choice(rng, INDUSTRY_WEIGHTS)
    else:
        # 75% of the time secondary mirrors primary (with minor & vs and variation)
        # 15% it gets bucketed into 'Others'
        # 10% it gets consolidated (e.g. "Manufacturing and Processing" → "Industrial Sector")
        r = rng.random()
        if r < 0.75:
            secondary = primary.replace(" and ", " & ")
        elif r < 0.90:
            secondary = "Others"
        else:
            consolidations = {
                "Manufacturing and Processing": "Industrial Sector",
                "Automotive Industry": "Industrial Sector",
                "Chemical Industry": "Industrial Sector",
                "Food Manufacturing and Processing": "Food Manufacturing & Processing",
                "Sports, Entertainment and Arts": "Entertainment and Arts",
            }
            secondary = consolidations.get(primary, primary)

    return primary, secondary


def generate_employees(rng: random.Random) -> int | None:
    """Most accounts have no employee count — ~4% populated (mirrors the real gap)."""
    if rng.random() > 0.04:
        return None
    # log-normal distribution for sizes
    return int(rng.lognormvariate(mu=2.5, sigma=1.4))


def generate_annual_revenue(rng: random.Random) -> float | None:
    """Annual revenue is even sparser — ~0.5% populated."""
    if rng.random() > 0.005:
        return None
    return round(rng.lognormvariate(mu=14.0, sigma=2.0), 2)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    rng = random.Random(SEED)
    Faker.seed(SEED)
    fake = Faker(["de_DE", "de_AT", "fr_FR", "nl_NL", "it_IT", "es_ES"])

    rows = []
    for _ in range(TOTAL_ACCOUNTS):
        country = weighted_choice(rng, COUNTRY_WEIGHTS)
        currency = CURRENCY_BY_COUNTRY.get(country, "EUR")
        account_type = weighted_choice(rng, ACCOUNT_TYPE_WEIGHTS)
        status = weighted_choice(rng, STATUS_WEIGHTS) if account_type.startswith("Customer") else None
        primary, secondary = generate_industry_pair(rng)

        # ARR only present for accounts that are actually customers
        is_paying = account_type in ("Customer", "Customer Churning") and status in ("active", "non_renewing")
        arr = synthetic_arr(rng) if is_paying else None

        rows.append({
            "account_id":             f"acc_{uuid.UUID(int=rng.getrandbits(128)).hex[:18]}",
            "account_name":           fake_company_name(fake, country),
            "account_type":           account_type,
            "customer_status":        status,
            "industry":               primary,
            "industry_sector_clean":  secondary,
            "contracted_arr":         arr,
            "account_currency":       currency,
            "billing_country":        country,
            "employees":              generate_employees(rng),
            "annual_revenue":         generate_annual_revenue(rng),
        })

    # Write CSV
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # Summary report
    print(f"✓ Wrote {len(rows):,} synthetic accounts to {OUTPUT_PATH}")
    print()
    print("Sanity checks:")
    by_status = {}
    by_type = {}
    arr_total = 0.0
    industry_filled = 0
    sector_filled = 0
    for r in rows:
        by_status[r["customer_status"]] = by_status.get(r["customer_status"], 0) + 1
        by_type[r["account_type"]] = by_type.get(r["account_type"], 0) + 1
        if r["contracted_arr"]:
            arr_total += r["contracted_arr"]
        if r["industry"]:
            industry_filled += 1
        if r["industry_sector_clean"]:
            sector_filled += 1

    print(f"  customer_status distribution: {by_status}")
    print(f"  account_type distribution:    {by_type}")
    print(f"  industry fill rate:           {100 * industry_filled / len(rows):.1f}%")
    print(f"  industry_sector fill rate:    {100 * sector_filled / len(rows):.1f}%")
    print(f"  total ARR (all rows):         €{arr_total:,.2f}")


if __name__ == "__main__":
    main()
