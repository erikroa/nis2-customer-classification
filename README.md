# NIS2 / DORA Customer Classification — Reference Implementation

A reusable analytics pattern for classifying a B2B SaaS customer base against the EU's **NIS2 Directive** (network and information security) and **DORA** (Digital Operational Resilience Act).

Runs end-to-end on synthetic data — clone, install, run, and you have a working classification of ~6,000 fake customers in under a minute. The pattern transfers directly to any CRM (Salesforce, HubSpot, Planhat) and any warehouse (Snowflake, BigQuery, DuckDB, Postgres).

---

## Why this exists

NIS2 transposition deadlines are landing across the EU through 2024–2026, and regulated customers are pushing security and reporting obligations onto their software vendors. The first question Compliance asks is straightforward: **"Which of our customers fall under NIS2 or DORA scope?"**

The query underneath that question turns out to be non-trivial:
- Industry data lives in one system (CRM), ARR lives across several (CRM + billing + finance)
- A single "industry" field is usually two fields with partial agreement
- "Active customer" is overloaded: account-type filters, lifecycle status, and billing status all matter
- NIS2 Essential vs Important tiering needs entity-size data that's typically <5% populated
- DORA overlaps NIS2 Annex 1 Finance but is a separate regime requiring its own flag

This repo is a worked example of how to handle each of those, **with the limitations explicitly named in the output** rather than swept under the rug.

---

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/<your-username>/nis2-customer-classification.git
cd nis2-customer-classification
pip install -r requirements.txt

# Step 1 — generate the synthetic dataset (deterministic, ~7,500 fake accounts)
python data/generate_synthetic_data.py

# Step 2 — run the full classification pipeline
python run_analysis.py
```

Outputs land in `output/`:
- `nis2_classification.csv` / `.xlsx` — one row per active customer
- `nis2_summary.csv` — headline counts and ARR per classification bucket

Expected console output:

```
Total active customers:          6,147
Total ARR:                     €  6,758,669.16
NIS2 in-scope:                   2,011 customers (32.7%)
NIS2 in-scope ARR:             €  2,244,386.17 (33.2%)
DORA-applicable:                   251 customers, €304,486.83 ARR
Unknown / needs review:            835 customers (13.6%)
```

---

## Repo structure

```
nis2-customer-classification/
├── README.md                          ← you are here
├── requirements.txt
├── run_analysis.py                    ← end-to-end runner
│
├── data/
│   ├── generate_synthetic_data.py     ← Faker-based generator (deterministic)
│   ├── synthetic_accounts.csv         ← generated input (committed for convenience)
│   └── dim_nis2_sector_mapping.csv    ← classification seed (Compliance-owned)
│
├── sql/
│   ├── 01_discovery.sql               ← profile fill rates, fields, scope
│   ├── 02_create_seed_table.sql       ← create + load the mapping table
│   ├── 03_classify_customers.sql      ← the main analysis
│   └── 04_summary.sql                 ← headline aggregates
│
└── docs/
    ├── methodology.md                 ← why coalesce, why this scope filter, etc.
    ├── nis2_dora_reference.md         ← quick regulatory primer
    └── limitations.md                 ← honest list of what this doesn't solve
```

---

## How it works

### 1. Source data — synthetic accounts

`data/generate_synthetic_data.py` produces 7,500 fake B2B accounts using the [Faker](https://faker.readthedocs.io/) library with a fixed seed. Realistic distributions across:

- **Industries**: ~30 distinct values, weighted toward construction/services/SMB sectors typical of a B2B fleet/SaaS book, with measurable populations in NIS2-relevant sectors (Energy, Health, Finance, Manufacturing, Transport)
- **Account types**: Customer, Customer Churning, Customer Lost, Prospect, Prosumer
- **Customer status**: active, non_renewing, cancelled, trial
- **ARR**: long-tail log-normal — median ~€600, max ~€100k
- **Size signals** (employees, annual_revenue): deliberately sparse — ~4% and ~0.5% populated, mirroring real-world coverage

Output: `data/synthetic_accounts.csv`.

### 2. Sector mapping — the seed table

`data/dim_nis2_sector_mapping.csv` is the source-of-truth for how each raw industry value maps to a NIS2 classification:

| source_value | nis2_classification | nis2_annex | dora_applicable | notes |
|---|---|---|---|---|
| Energy Industry | Essential Entity | Annex 1 | FALSE | … |
| Finance and Insurance Services | Essential Entity | Annex 1 | TRUE | DORA split needed |
| Manufacturing and Processing | Important Entity | Annex 2 | FALSE | … |
| Construction and Engineering | Out of scope | N/A | FALSE | … |
| IT Service | Unknown | Annex 1? | FALSE | MSP/MSSP split required |

**This file is meant to be edited by Compliance, not by analysts.** Adding a new industry value or changing how one is classified is a CSV edit + re-load, not a code change.

### 3. The pipeline

`run_analysis.py` orchestrates four SQL steps against a DuckDB in-memory database:

1. **Discovery** (`sql/01_discovery.sql`) — profiles account-type breakdowns, industry fill rates, value distributions, and size-data sparsity. Tells you whether the data supports the analysis before you build it.
2. **Seed load** (`sql/02_create_seed_table.sql`) — creates `dim_nis2_sector_mapping` and copies the CSV in.
3. **Classification** (`sql/03_classify_customers.sql`) — joins active customers to the sector mapping, produces one row per customer with NIS2 classification + DORA flag + size tier indicator.
4. **Summary** (`sql/04_summary.sql`) — aggregates to headline counts and ARR per classification bucket.

See `docs/methodology.md` for the reasoning behind each design choice.

---

## Porting to a real warehouse

The SQL is written in standard ANSI/DuckDB dialect. Differences when porting:

### Snowflake
- `MEDIAN()` works identically
- `COPY` uses stages: stage the CSV via `PUT file://... @~/` or external stage, then `COPY INTO dim_nis2_sector_mapping FROM @stage_name FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)`
- For one-off seeding, easiest path is Snowsight's "Load Data" UI button on the table
- Fully-qualify everything (`DATABASE.SCHEMA.TABLE`) to avoid context-bound errors

### BigQuery
- Replace `MEDIAN()` with `APPROX_QUANTILES(value, 100)[OFFSET(50)]`
- Replace `BOOLEAN` with `BOOL` in DDL
- Load via `bq load --source_format=CSV --skip_leading_rows=1 dataset.dim_nis2_sector_mapping data/dim_nis2_sector_mapping.csv`

### Postgres
- Works essentially as-is
- `\copy dim_nis2_sector_mapping FROM 'data/dim_nis2_sector_mapping.csv' CSV HEADER;`

### dbt
- Move `dim_nis2_sector_mapping.csv` to `seeds/`, add a `seeds.yml` with column types, run `dbt seed`
- The classification query becomes a `models/nis2_classification.sql` referencing the seed via `{{ ref('dim_nis2_sector_mapping') }}`
- This is the right home for production: Compliance edits the seed CSV in a PR, dbt re-seeds on next run, downstream consumers always see the current mapping

---

## What this is and isn't

**Is:**
- A reference implementation of a classification pattern that works across CRMs and warehouses
- A worked example of how to do regulatory scoping honestly — surfacing limitations rather than papering over them
- A starting point for an analyst hitting a NIS2/DORA scoping ask for the first time

**Isn't:**
- A legal classification system. Regulatory determination of any individual entity is a legal call, not a SQL output.
- A production-ready pipeline. Output schemas would need orchestration (Airflow/dbt), monitoring, alerting, and freshness checks before going operational.
- A complete NIS2 implementation guide. See `docs/nis2_dora_reference.md` for scope, and consult primary regulatory sources for compliance.

The synthetic data is **fully fictional** — generated procedurally from a fixed Faker seed. Any resemblance to real organizations is coincidental.

See `docs/limitations.md` for a full list of what this pipeline can't tell you.

---

## License

MIT.
