-- =====================================================================
-- 01_discovery.sql — Discovery and profiling of the source data
-- =====================================================================
-- This script profiles the source `accounts` table to answer:
--   1. How many active customers do we have, and how is "active" defined?
--   2. Which industry field has better coverage?
--   3. Do the two industry fields agree where both are populated?
--   4. Can we use entity-size data (employees, annual_revenue) for NIS2
--      Essential vs Important tiering?
--
-- Run order: this is step 1 — before creating the seed table or running
-- the classification. Each query is independent and safe to re-run.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Account-type breakdown across customer_status
--    Find what "active" actually means in the data
-- ---------------------------------------------------------------------
SELECT
    account_type,
    customer_status,
    COUNT(*)              AS account_count,
    ROUND(SUM(contracted_arr), 2) AS total_arr
FROM accounts
GROUP BY account_type, customer_status
ORDER BY account_type, customer_status;


-- ---------------------------------------------------------------------
-- 2. Active customer count under the intended scope
--    "Customer" type + active/non_renewing status
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                              AS active_customers,
    ROUND(SUM(contracted_arr), 2)         AS total_arr,
    ROUND(AVG(contracted_arr), 2)         AS avg_arr,
    ROUND(MEDIAN(contracted_arr), 2)      AS median_arr
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing');


-- ---------------------------------------------------------------------
-- 3. Fill rates for the two industry fields (within active scope)
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                                                              AS active_customers,
    COUNT(industry)                                                                       AS has_industry,
    COUNT(industry_sector_clean)                                                          AS has_industry_sector,
    ROUND(100.0 * COUNT(industry)             / COUNT(*), 1)                              AS pct_industry,
    ROUND(100.0 * COUNT(industry_sector_clean) / COUNT(*), 1)                             AS pct_industry_sector,
    SUM(CASE WHEN industry IS NOT NULL AND industry_sector_clean IS NOT NULL THEN 1 END) AS both_populated,
    SUM(CASE WHEN industry IS NULL     AND industry_sector_clean IS NOT NULL THEN 1 END) AS only_sector,
    SUM(CASE WHEN industry IS NOT NULL AND industry_sector_clean IS NULL     THEN 1 END) AS only_industry,
    SUM(CASE WHEN industry IS NULL     AND industry_sector_clean IS NULL     THEN 1 END) AS neither
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing');


-- ---------------------------------------------------------------------
-- 4. Distinct values in each industry field (input to the mapping table)
-- ---------------------------------------------------------------------
SELECT 'industry' AS source_field, industry AS value, COUNT(*) AS active_customers
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing')
  AND industry IS NOT NULL
GROUP BY 1, 2
UNION ALL
SELECT 'industry_sector_clean', industry_sector_clean, COUNT(*)
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing')
  AND industry_sector_clean IS NOT NULL
GROUP BY 1, 2
ORDER BY source_field, active_customers DESC;


-- ---------------------------------------------------------------------
-- 5. Agreement cross-tab: where both fields are populated, do they agree?
-- ---------------------------------------------------------------------
SELECT industry, industry_sector_clean, COUNT(*) AS n
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing')
  AND industry IS NOT NULL
  AND industry_sector_clean IS NOT NULL
GROUP BY 1, 2
ORDER BY n DESC
LIMIT 50;


-- ---------------------------------------------------------------------
-- 6. Size-data fill rates — for NIS2 Essential vs Important tiering
-- ---------------------------------------------------------------------
-- NIS2 Essential vs Important tiering depends on entity size:
--   - Essential (Annex 1) = large enterprise (>=250 employees OR turnover >=50M EUR)
--   - Important (Annex 2 / medium Annex 1) = medium (50-249 employees / 10-50M EUR)
-- This check tells you whether you can defensibly do that split.
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                              AS active_customers,
    COUNT(employees)                                      AS has_employees,
    COUNT(annual_revenue)                                 AS has_annual_revenue,
    ROUND(100.0 * COUNT(employees)       / COUNT(*), 1)   AS pct_employees,
    ROUND(100.0 * COUNT(annual_revenue)  / COUNT(*), 1)   AS pct_annual_revenue
FROM accounts
WHERE account_type = 'Customer'
  AND customer_status IN ('active', 'non_renewing');
