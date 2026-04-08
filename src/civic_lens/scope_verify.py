"""Scope verification script for Phase 6."""

from __future__ import annotations

import sys

import pandas as pd


def run_scope_assertions(
    dim_path: str,
    results_path: str,
) -> bool:
    dim = pd.read_csv(dim_path)
    df = pd.read_csv(results_path, low_memory=False)

    passed = True

    active = dim[dim["election_active_2026"] == True]
    tier1 = active[active["tier"] == 1]
    tier2 = active[active["tier"] == 2]
    tier3 = active[active["tier"] == 3]

    tier1 = active[
        active["authority_code"].str.startswith("E08", na=False)
        & active["tier"].isin([1, 3])
    ]
    if len(tier1) != 32:
        print(f"FAIL: Tier 1 active: expected 32, got {len(tier1)}")
        print(tier1["authority_name"].sort_values().tolist())
        passed = False
    else:
        print(f"PASS: Tier 1 active = {len(tier1)}")

    if len(tier2) != 32:
        print(f"FAIL: Tier 2 active: expected 32, got {len(tier2)}")
        passed = False
    else:
        print(f"PASS: Tier 2 active = {len(tier2)}")

    if len(tier3) != 5:
        print(f"FAIL: Tier 3 active: expected 5, got {len(tier3)}")
        print(tier3["authority_name"].sort_values().tolist())
        passed = False
    else:
        print(f"PASS: Tier 3 active = {len(tier3)}")

    EXCLUDED_CODES = {"E08000017", "E08000012", "E08000015", "E08000018"}
    active_codes = set(active["authority_code"])
    overlap = EXCLUDED_CODES & active_codes
    if overlap:
        print(f"FAIL: Excluded authorities appear in active scope: {overlap}")
        passed = False
    else:
        print("PASS: All 4 excluded MBs absent from active scope")

    dim_excluded = dim[dim["authority_code"].isin(EXCLUDED_CODES)]
    if dim_excluded["election_active_2026"].any():
        print("FAIL: Excluded MBs marked election_active_2026=True in dimension table")
        passed = False
    else:
        print("PASS: Excluded MBs correctly flagged election_active_2026=False")

    WY_CODES = {"E08000032", "E08000033", "E08000034", "E08000035", "E08000036"}
    wy_in_dim = set(dim[dim["authority_code"].isin(WY_CODES)]["authority_code"])
    if wy_in_dim != WY_CODES:
        missing = WY_CODES - wy_in_dim
        print(f"FAIL: West Yorkshire codes missing from dimension: {missing}")
        passed = False
    else:
        print("PASS: All 5 West Yorkshire councils present as Tier 3")

    wy_type = dim[dim["authority_code"].isin(WY_CODES)]["authority_type"].unique()
    if not (len(wy_type) == 1 and wy_type[0] == "west_yorkshire_mb"):
        print(f"FAIL: West Yorkshire authority_type wrong: {wy_type}")
        passed = False
    else:
        print("PASS: West Yorkshire correctly typed as west_yorkshire_mb")

    london_in_dim = dim[
        (dim["authority_type"] == "london_borough")
        & (dim["authority_code"] != "E09000001")
    ]
    if len(london_in_dim) != 32:
        print(f"FAIL: London boroughs: expected 32, got {len(london_in_dim)}")
        passed = False
    else:
        print("PASS: 32 London boroughs present as Tier 2")

    active_rows = df[df["authority_code"].isin(active_codes)]
    geo_cols = ["authority_code", "authority_name", "authority_type", "region", "tier"]
    for col in geo_cols:
        null_count = active_rows[col].isna().sum()
        if null_count > 0:
            print(f"FAIL: {null_count} active rows have null {col}")
            passed = False
        else:
            print(f"PASS: {col} fully populated for active rows")

    valid_types = {"metropolitan_borough", "london_borough", "west_yorkshire_mb"}
    actual_types = set(df["authority_type"].dropna().unique())
    unexpected = actual_types - valid_types
    if unexpected:
        print(f"FAIL: Unexpected authority_type values: {unexpected}")
        passed = False
    else:
        print("PASS: authority_type values all valid")

    return passed


if __name__ == "__main__":
    ok = run_scope_assertions(
        "data/processed/authority_dimension.csv",
        "data/processed/clean_election_results.csv",
    )
    sys.exit(0 if ok else 1)
