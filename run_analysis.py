"""
End-to-end demo runner for the NIS2 customer classification pipeline.

Loads the synthetic accounts CSV into DuckDB, creates the sector mapping
seed table from the CSV, runs the classification, and exports both the
full classification and the summary to CSV/Excel.

Run order assumes data/synthetic_accounts.csv exists (run
`python data/generate_synthetic_data.py` first if not).

Usage:
    python run_analysis.py

Output (in `output/`):
    - nis2_classification.csv      (one row per active customer)
    - nis2_classification.xlsx     (same, Excel-formatted)
    - nis2_summary.csv             (headline counts/ARR per bucket)
"""

from __future__ import annotations

from pathlib import Path

try:
    import duckdb
except ImportError:
    raise SystemExit("DuckDB is required. Install with: pip install duckdb")

try:
    import pandas as pd  # for Excel export
except ImportError:
    raise SystemExit("pandas is required. Install with: pip install pandas openpyxl")


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "output"


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    # Verify inputs exist
    accounts_csv = DATA_DIR / "synthetic_accounts.csv"
    mapping_csv = DATA_DIR / "dim_nis2_sector_mapping.csv"
    if not accounts_csv.exists():
        raise SystemExit(
            f"Missing {accounts_csv}.\n"
            f"Run `python {DATA_DIR / 'generate_synthetic_data.py'}` first."
        )
    if not mapping_csv.exists():
        raise SystemExit(f"Missing {mapping_csv}")

    print(f"Loading {accounts_csv.name}...")
    con = duckdb.connect()
    con.execute(
        f"CREATE TABLE accounts AS SELECT * FROM read_csv_auto('{accounts_csv}', header=true)"
    )
    n_total = con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    print(f"  → {n_total:,} accounts loaded")

    print("\nCreating sector mapping seed table...")
    # We inline the seed creation rather than running the .sql file directly,
    # because the .sql file uses a relative COPY path that breaks if you run
    # this script from a different working directory.
    con.execute("""
        DROP TABLE IF EXISTS dim_nis2_sector_mapping;
        CREATE TABLE dim_nis2_sector_mapping (
            source_value         TEXT      NOT NULL PRIMARY KEY,
            nis2_classification  TEXT,
            nis2_annex           TEXT,
            nis2_sub_sector      TEXT,
            dora_applicable      BOOLEAN,
            notes_for_compliance TEXT
        );
    """)
    con.execute(f"COPY dim_nis2_sector_mapping FROM '{mapping_csv}' (HEADER, AUTO_DETECT TRUE);")
    n_mapping = con.execute("SELECT COUNT(*) FROM dim_nis2_sector_mapping").fetchone()[0]
    print(f"  → {n_mapping} sector mappings loaded")

    print("\nRunning classification...")
    classification = con.execute((SQL_DIR / "03_classify_customers.sql").read_text()).fetchdf()
    print(f"  → {len(classification):,} active customers classified")

    print("\nRunning summary...")
    summary = con.execute((SQL_DIR / "04_summary.sql").read_text()).fetchdf()

    # Save outputs
    classification_csv = OUT_DIR / "nis2_classification.csv"
    classification_xlsx = OUT_DIR / "nis2_classification.xlsx"
    summary_csv = OUT_DIR / "nis2_summary.csv"

    classification.to_csv(classification_csv, index=False)
    classification.to_excel(classification_xlsx, index=False)
    summary.to_csv(summary_csv, index=False)

    print(f"\n✓ Wrote {classification_csv}")
    print(f"✓ Wrote {classification_xlsx}")
    print(f"✓ Wrote {summary_csv}")

    # Print the executive summary inline
    print("\n" + "=" * 70)
    print("CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(summary.to_string(index=False))

    # Headline takeaways
    print("\n" + "=" * 70)
    print("HEADLINE TAKEAWAYS")
    print("=" * 70)
    in_scope_customers = int(
        summary[summary["classification"].isin(["Essential Entity", "Important Entity"])]["customer_count"].sum()
    )
    in_scope_arr = float(
        summary[summary["classification"].isin(["Essential Entity", "Important Entity"])]["total_arr"].sum()
    )
    dora_customers = int(summary[summary["dora_applicability"]]["customer_count"].sum())
    dora_arr = float(summary[summary["dora_applicability"]]["total_arr"].sum())
    total_customers = int(summary["customer_count"].sum())
    total_arr = float(summary["total_arr"].sum())
    unknown_customers = int(summary[summary["classification"] == "Unknown"]["customer_count"].sum())

    print(f"Total active customers:        {total_customers:>7,}")
    print(f"Total ARR:                     €{total_arr:>14,.2f}")
    print(f"NIS2 in-scope:                 {in_scope_customers:>7,} customers "
          f"({100 * in_scope_customers / total_customers:.1f}%)")
    print(f"NIS2 in-scope ARR:             €{in_scope_arr:>14,.2f} "
          f"({100 * in_scope_arr / total_arr:.1f}%)")
    print(f"DORA-applicable:               {dora_customers:>7,} customers, "
          f"€{dora_arr:,.2f} ARR")
    print(f"Unknown / needs review:        {unknown_customers:>7,} customers "
          f"({100 * unknown_customers / total_customers:.1f}%)")


if __name__ == "__main__":
    main()
