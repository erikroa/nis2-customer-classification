-- =====================================================================
-- 03_classify_customers.sql — NIS2 / DORA customer classification
-- =====================================================================
-- Produces one row per active customer with:
--   - Identifying info (id, name, country, currency)
--   - Contracted ARR
--   - Resolved industry (primary field with cleaned-secondary fallback)
--   - NIS2 classification (Essential / Important / Out of scope / Unknown)
--   - NIS2 Annex (1 or 2)
--   - DORA applicability flag
--   - Entity size tier indicator (with explicit "data insufficient" flag)
--
-- This is the result set you export to Excel/CSV for Compliance.
--
-- Scope assumptions:
--   - account_type = 'Customer' (excludes Churning/Lost/Prospect)
--   - customer_status IN ('active', 'non_renewing') (excludes Cancelled/Trial)
--   - Industry classification uses coalesce(primary, secondary) for max coverage
-- =====================================================================

WITH active_customers AS (
    SELECT
        account_id,
        account_name,
        account_type,
        customer_status,
        contracted_arr,
        account_currency,
        billing_country,
        employees,
        annual_revenue,
        industry,
        industry_sector_clean,
        COALESCE(industry, industry_sector_clean)               AS resolved_industry,
        CASE
            WHEN industry IS NOT NULL              THEN 'industry'
            WHEN industry_sector_clean IS NOT NULL THEN 'industry_sector_clean'
            ELSE 'NONE'
        END                                                     AS resolved_industry_source
    FROM accounts
    WHERE account_type = 'Customer'
      AND customer_status IN ('active', 'non_renewing')
)
SELECT
    ac.account_id,
    ac.account_name                                             AS customer_name,
    ac.contracted_arr,
    ac.account_currency,
    ac.billing_country,
    ac.resolved_industry                                        AS sector,
    ac.resolved_industry_source,
    COALESCE(m.nis2_classification, 'Unknown')                  AS classification,
    m.nis2_annex,
    m.nis2_sub_sector,
    COALESCE(m.dora_applicable, FALSE)                          AS dora_applicability,
    ac.employees,
    ac.annual_revenue,
    CASE
        WHEN ac.employees >= 250 OR ac.annual_revenue >= 50000000 THEN 'Large (Essential candidate)'
        WHEN ac.employees >= 50  OR ac.annual_revenue >= 10000000 THEN 'Medium (Important candidate)'
        WHEN ac.employees IS NOT NULL OR ac.annual_revenue IS NOT NULL THEN 'Small/Micro'
        ELSE 'Size unknown — manual review required'
    END                                                         AS size_tier_indicator,
    ac.customer_status,
    m.notes_for_compliance
FROM active_customers ac
LEFT JOIN dim_nis2_sector_mapping m
    ON m.source_value = ac.resolved_industry
ORDER BY
    CASE COALESCE(m.nis2_classification, 'Unknown')
        WHEN 'Essential Entity' THEN 1
        WHEN 'Important Entity' THEN 2
        WHEN 'Unknown'          THEN 3
        ELSE 4
    END,
    ac.contracted_arr DESC NULLS LAST;
