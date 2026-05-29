# Limitations

What this pipeline can't tell you — and what to do about each one.

## 1. Industry data only exists for the CRM-touched customer subset

The biggest structural limitation.

**The problem.** In most B2B SaaS data architectures:
- **ARR** is tracked across multiple systems: CRM (contracted ARR for B2B accounts), billing platform (Chargebee, Stripe — recurring subscriptions), finance system (NetSuite, Quickbooks — invoiced revenue)
- **Industry** is captured only in the CRM, during the sales motion

This creates an asymmetry: total active ARR may span 50,000+ customers across all systems, but only the CRM-touched subset (often 5,000–10,000) has an industry value. The remaining customers — typically self-service or legacy — have no classifiable signal.

**The implication.** A pipeline like this can only classify the CRM-touched subset. Reporting it as "the active customer base" without that caveat misrepresents scope.

**Mitigations.**
- Explicitly scope the deliverable as "active customers with industry data captured in CRM" — and quantify the unclassified tail alongside it
- For the unclassified tail, recommend external enrichment (Clearbit, Dun & Bradstreet, ZoomInfo) against billing-domain data
- Long-term: change the data-collection process so industry is captured at sign-up in the billing/self-service flow, not just in the CRM

## 2. Essential vs Important tiering depends on size data that's usually missing

NIS2 distinguishes Essential (large) from Important (medium) entities by employee count and revenue. In typical CRM data:
- `employees` is populated <5% of the time
- `annual_revenue` is populated <1% of the time

**The pipeline's response.** Classifies Essential vs Important based on **sector alone**, and flags every record with `size_tier_indicator = 'Size unknown — manual review required'`. The few records with size data get a meaningful indicator, but the column is independent of the main classification.

**Don't treat the Essential/Important split here as final.** It's a defensible first pass for triage. For formal regulatory submission, each Essential candidate needs to be reviewed individually with corroborating data (D&B, Bundesanzeiger filings, etc.).

## 3. Multi-sector customers are hidden

A single industry field can only describe one business activity. In reality:
- A holding company might own a hospital AND a real-estate arm
- A diversified manufacturer might do automotive AND chemicals AND food
- A "telco" might also be a managed service provider

The pipeline picks one classification per customer based on the single industry value. Customers with material activity in multiple regulated sectors will only show the primary one.

**Mitigation.** Where Compliance flags this as a real concern, augment the analysis with parent-company data, public filings, or website-scraping for activity codes.

## 4. The "IT Service" classification problem

"IT Service" is a common industry value that genuinely splits across NIS2 categories:
- **In scope (Annex 1):** Managed service providers (MSPs), managed security service providers (MSSPs), cloud providers, content delivery networks
- **Out of scope:** Pure IT consulting, custom software development, integration services

A single industry field can't distinguish these. The pipeline puts all "IT Service" records into the Unknown bucket explicitly, with a `notes_for_compliance` flag — better than guessing.

**Mitigation.** Manual classification of IT Service customers, possibly using:
- Customer-website content analysis
- Product/service descriptions in onboarding notes
- A dedicated CRM custom field captured during account creation

## 5. Sector mapping is starter-quality, not legally vetted

The mappings in `dim_nis2_sector_mapping.csv` are an analyst's first-pass interpretation of how common CRM industry values map to NIS2 Annex 1/2. Regulatory classification is a legal determination that requires:
- Cross-reference to the entity's actual licensed activities
- Jurisdictional context (NIS2 transposition varies by member state)
- Sometimes case-by-case judgment on edge cases (e.g. when does a tech company become a "digital service provider"?)

**The seed table is owned by Compliance, not Analytics.** This pipeline produces an editable starting point; the final mapping is the regulator-facing artifact and needs human review before any classification leaves the building.

## 6. Static snapshot, not a stream

The pipeline produces a point-in-time classification from the current state of the source data. It doesn't:
- Track entries/exits from scope over time (a customer becoming Essential as they grow)
- Trigger alerts when a new customer signs up in a regulated sector
- Reconcile against prior-period classifications

For ongoing regulatory monitoring, you'd want to:
- Persist the output to a versioned table with a `classification_date`
- Compare period-over-period to surface new-in-scope and dropped-from-scope customers
- Wire a notification when a high-priority sector (Banking, Energy, Health) closes-won

## 7. Data freshness and lineage

The pipeline doesn't inspect data freshness. If the CRM industry field is stale (entered at customer creation 5 years ago, never updated through a pivot), the classification reflects the stale data.

**Mitigation.** Add a `last_updated_at` column to the source query and surface it in the output. Records with `industry` last updated more than 24 months ago should be flagged for refresh.

## What this means practically

These limitations don't make the analysis useless — they make it **honest**. The right framing for a Compliance audience:

> "This pipeline classifies [X,XXX] customers with industry data captured in CRM, representing [Y%] of our active customer base by count and [Z%] by ARR. The classification is sector-only (size data insufficient for Essential/Important tiering) and represents an analyst's first-pass interpretation of the NIS2 Annexes — final regulatory classification requires per-entity legal review. The unclassified [W%] tail represents customers without industry data in any source system and requires enrichment before broader scoping is possible."

That paragraph is the difference between an analysis that survives scrutiny and one that doesn't.
