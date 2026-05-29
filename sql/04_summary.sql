-- =====================================================================
-- 04_summary.sql — Headline numbers for the executive briefing
-- =====================================================================
-- Aggregates the classification output into a small summary table:
--   - Customer count per classification bucket
--   - Total ARR per bucket
--   - DORA-applicable subset
--
-- This is what you paste into the email/Slack to Compliance.
-- =====================================================================

WITH classified AS (
    SELECT
        a.contracted_arr,
        COALESCE(m.nis2_classification, 'Unknown') AS classification,
        COALESCE(m.dora_applicable, FALSE)         AS dora_applicability
    FROM accounts a
    LEFT JOIN dim_nis2_sector_mapping m
        ON m.source_value = COALESCE(a.industry, a.industry_sector_clean)
    WHERE a.account_type = 'Customer'
      AND a.customer_status IN ('active', 'non_renewing')
)
SELECT
    classification,
    dora_applicability,
    COUNT(*)                                AS customer_count,
    ROUND(SUM(contracted_arr), 2)           AS total_arr,
    ROUND(AVG(contracted_arr), 2)           AS avg_arr,
    ROUND(MEDIAN(contracted_arr), 2)        AS median_arr
FROM classified
GROUP BY classification, dora_applicability
ORDER BY
    CASE classification
        WHEN 'Essential Entity' THEN 1
        WHEN 'Important Entity' THEN 2
        WHEN 'Unknown'          THEN 3
        ELSE 4
    END,
    dora_applicability DESC;
