# Methodology

How the classification is built, and why.

## Source data shape

The pipeline assumes a B2B SaaS customer table (`accounts`) with these fields:

| Field | Purpose |
|---|---|
| `account_id` | Primary key |
| `account_name` | Display name |
| `account_type` | Lifecycle bucket (Customer, Prospect, Churning, Lost) |
| `customer_status` | Billing status (active, non_renewing, cancelled, etc.) |
| `industry` | Primary industry — often a standard CRM picklist |
| `industry_sector_clean` | Secondary, cleaned industry field — often a custom field maintained by RevOps |
| `contracted_arr` | Annual recurring revenue |
| `billing_country`, `account_currency` | Geographic/financial context |
| `employees`, `annual_revenue` | Entity-size signals (often very sparsely populated) |

In a real warehouse these come from Salesforce, HubSpot, Planhat, or a combination — but the analytical pattern is the same.

## Scope rule: what counts as an "active customer"

Two filters, applied together:

```sql
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing')
```

**Why both filters matter.** `customer_status = 'active'` alone is often too permissive — in many CRM data-warehouse implementations it surfaces records that are technically in an "active" lifecycle state but aren't really billing customers (Prospects, Churning, Lost). The `account_type = 'Customer'` filter strips those out.

**Why include `non_renewing`.** Customers in their notice period are still under contract until the renewal date — they're in regulatory scope until they actually leave.

**Why this matters for regulatory work.** A scope leak here doesn't just inflate numbers; it produces a classification that includes prospects and churned accounts, which is wrong by definition for "current regulated customers."

## Industry resolution: coalesce, don't choose

Most CRMs end up with multiple industry fields over time — a standard picklist that's been around forever, a "cleaner" custom field that someone added later. They typically have different fill rates and slightly different vocabularies.

The pipeline uses a coalesce strategy:

```sql
COALESCE(industry, industry_sector_clean) AS resolved_industry
```

**Why coalesce instead of picking one.** Both fields have gaps. Coalesce captures customers where only one is populated, which can lift coverage 5–15 percentage points over picking either field alone.

**Why primary first.** In the demonstrated dataset, `industry` has higher fill (~80%) and more specific values; `industry_sector_clean` tends to consolidate buckets (e.g. dumping uncertain records to "Others"). Picking the more-specific field as primary preserves classification signal.

**Tracking source for audit.** The output includes a `resolved_industry_source` column showing which field supplied each value. This lets Compliance later see whether a record was classified from the standard or the custom field — useful when reviewing borderline classifications.

## NIS2 sector mapping: a seed table, not inline CASE WHEN

Mapping raw industry values to NIS2 classifications could be done as a long `CASE WHEN` block in the main query. The pipeline doesn't do that — it uses a seed table (`dim_nis2_sector_mapping`) loaded from a CSV that Compliance owns.

**Why a seed table.**
- Compliance can edit the mapping in a Sheet/CSV and re-seed, without touching SQL
- The mapping becomes an auditable artifact in its own right (versioned, reviewable)
- The main query stays clean — a single JOIN, not 40+ inline conditions
- Adding a new industry value to the source data means adding one row to the seed, not editing the query

**Trade-off.** Operational complexity — you have two artifacts to keep in sync. For a one-off analysis this is overkill; for ongoing regulatory reporting it's the right call.

## Essential vs Important tiering: sector-only, with explicit size caveat

NIS2 distinguishes Essential Entities (large + Annex 1) from Important Entities (medium + Annex 1 or any size + Annex 2). The size dimension is mostly unavailable in CRM data — both real and synthetic datasets show `employees` populated <5% and `annual_revenue` <1%.

The pipeline's response:

```sql
CASE
    WHEN employees >= 250 OR annual_revenue >= 50000000 THEN 'Large (Essential candidate)'
    WHEN employees >= 50  OR annual_revenue >= 10000000 THEN 'Medium (Important candidate)'
    WHEN employees IS NOT NULL OR annual_revenue IS NOT NULL THEN 'Small/Micro'
    ELSE 'Size unknown — manual review required'
END AS size_tier_indicator
```

**Two principles here.**
1. **Surface what you have, even if sparse.** The few records with size data get a meaningful tier.
2. **Flag what you don't have explicitly.** "Size unknown — manual review required" is a defensible deliverable; assigning Essential/Important based on sector alone and *calling it final* is not.

The Essential/Important *classification* column comes from the sector mapping alone (since most size data is missing). The `size_tier_indicator` is an independent signal, intended to be combined with classification during human review — not used as a hard filter in the SQL.

## DORA as a flag, not a separate classification

DORA applies to financial-sector entities — most of which also fall under NIS2 Annex 1 Finance. Rather than treating DORA as a fourth classification value (Essential/Important/Out-of-scope/DORA), the pipeline models DORA as a boolean flag *on top of* the NIS2 classification:

```sql
dora_applicable BOOLEAN  -- in the seed table
```

A bank is `classification = 'Essential Entity'` AND `dora_applicability = TRUE`. An insurance broker might be `classification = 'Essential Entity'` AND `dora_applicability = FALSE` (or true, depending on the broker type — Compliance call). This avoids forcing the regulator's two-axis model into a single column.

## What this pipeline doesn't try to do

- **It doesn't classify what has no industry data.** Records with `resolved_industry = NULL` (neither field populated) end up as `Unknown`. The pipeline doesn't try to infer industry from company name, domain, or billing country.
- **It doesn't reconcile across systems.** In real environments, ARR often comes from Billing (Chargebee, Stripe) while industry comes from CRM (Salesforce). The pipeline assumes both are already in the same source table. The README discusses why this matters.
- **It doesn't enforce uniqueness across the mapping.** PRIMARY KEY on `source_value` is defined but not all SQL engines enforce it. The discovery script includes a duplicate-check query.
- **It doesn't determine final regulatory scope.** This is a Compliance-facing analyst tool, not a legal classification system. The output is the input to a Compliance review, not a substitute for one.
