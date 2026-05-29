-- =====================================================================
-- 02_create_seed_table.sql — NIS2 sector mapping seed table
-- =====================================================================
-- Creates `dim_nis2_sector_mapping` and loads the classification
-- from data/dim_nis2_sector_mapping.csv.
--
-- This is the single source of truth for how raw industry values
-- (e.g. "Energy Industry", "IT Service") map to NIS2 classifications
-- (Essential Entity / Important Entity / Out of scope / Unknown) and
-- DORA applicability.
--
-- Compliance owns this file. Analysts read it; Compliance edits it.
-- =====================================================================

DROP TABLE IF EXISTS dim_nis2_sector_mapping;

CREATE TABLE dim_nis2_sector_mapping (
    source_value         TEXT      NOT NULL PRIMARY KEY,
    nis2_classification  TEXT,     -- Essential Entity | Important Entity | Out of scope | Unknown
    nis2_annex           TEXT,     -- Annex 1 | Annex 2 | N/A
    nis2_sub_sector      TEXT,
    dora_applicable      BOOLEAN,
    notes_for_compliance TEXT
);

-- Load from CSV (DuckDB syntax; for Snowflake/BigQuery see notes in README)
COPY dim_nis2_sector_mapping FROM 'data/dim_nis2_sector_mapping.csv' (HEADER, AUTO_DETECT TRUE);


-- ---------------------------------------------------------------------
-- Sanity check the load
-- ---------------------------------------------------------------------
SELECT nis2_classification, COUNT(*) AS sector_values
FROM dim_nis2_sector_mapping
GROUP BY 1
ORDER BY 1;

-- Verify no duplicate source values
SELECT source_value, COUNT(*) AS dupes
FROM dim_nis2_sector_mapping
GROUP BY source_value
HAVING COUNT(*) > 1;
-- Expected: zero rows
