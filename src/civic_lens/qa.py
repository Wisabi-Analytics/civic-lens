"""Phase 8 QA checks and reporting."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

scripts_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(scripts_root))

RESULTS: list[dict[str, object]] = []


def add_result(check_id: str, check_type: str, description: str, n_affected: int,
               denominator: int, threshold_pct: float | None = None,
               notes: str = "") -> int:
    pct = (n_affected / denominator * 100) if denominator > 0 else 0.0
    if check_type == "HARD":
        status = "FAIL" if n_affected > 0 else "PASS"
    elif check_type == "WARN":
        status = "WARN" if n_affected > 0 else "PASS"
    else:
        status = "INFO"
    RESULTS.append({
        "check_id": check_id,
        "check_type": check_type,
        "description": description,
        "n_affected": n_affected,
        "pct_affected": round(pct, 3),
        "threshold": threshold_pct,
        "status": status,
        "notes": notes,
    })
    icon = "✓" if status == "PASS" else ("⚠" if status in ("WARN", "INFO") else "✗")
    print(f"  {icon} [{check_id}] {description}: {n_affected:,} ({pct:.2f}%)")
    return n_affected


def main() -> None:
    data_root = Path("data/processed")
    df_path = data_root / "clean_election_results.csv"

    df = pd.read_csv(df_path, low_memory=False)
    active = df[df["analysis_level"].isin(["ward", "borough_fallback"])].copy()
    borough_only = df[df["analysis_level"] == "borough_only"].copy()
    desc_only = df[df["analysis_level"] == "descriptive_only"].copy()
    leap_only = df[df["data_source_era"] == "leap_only"].copy()
    dc_leap = df[df["data_source_era"] == "dc_leap"].copy()
    dcl = df[df["source_dataset"].str.startswith("dcleapil")].copy()
    commons22 = df[df["source_dataset"] == "commons_2022"].copy()
    dcl_2022 = df[df["source_dataset"] == "dcleapil_2022"].copy()

    print(f"Total rows:          {len(df):,}")
    print(f"Active (ward/bf):    {len(active):,}")
    print(f"Borough-only:        {len(borough_only):,}")
    print(f"Descriptive-only:    {len(desc_only):,}")
    print(f"leap_only rows:      {len(leap_only):,}")
    print(f"Commons 2022 rows:   {len(commons22):,}")

    denom_all = len(df)
    denom_vs = df["vote_share"].dropna().shape[0]

    print("\n── HARD ASSERTIONS ──")
    # H01
    h01 = (df["votes"] < 0).sum()
    add_result("H01", "HARD", "Negative vote counts", h01, denom_all)

    # H02
    vs = df["vote_share"].dropna()
    h02 = ((vs < 0) | (vs > 100)).sum()
    add_result("H02", "HARD", "vote_share outside [0,100]", h02, len(vs))

    # H03
    h03 = (df["seats_won"] > df["seats_contested"]).sum()
    add_result("H03", "HARD", "seats_won > seats_contested", h03, denom_all)

    # H04
    h04 = (~df["seats_contested"].isin([1, 2, 3])).sum()
    add_result("H04", "HARD", "seats_contested not in {1,2,3}", h04, denom_all)

    # H05
    h05 = ((df["elected"] == True) & (df["seats_won"] != 1)).sum() + \
          ((df["elected"] == False) & (df["seats_won"] != 0)).sum()
    add_result("H05", "HARD", "seats_won inconsistent with elected", h05, denom_all)

    # H06
    has_both = (
        df["votes"].notna() &
        df["total_valid_votes"].notna() &
        (df["total_valid_votes"] > 0) &
        ~df["analysis_level"].isin(["borough_only", "descriptive_only"])
    )
    h06 = (has_both & df["vote_share"].isna()).sum()
    add_result("H06", "HARD",
               "vote_share null where votes and total_valid_votes present", h06, has_both.sum())

    # H07
    derivable = df[
        has_both &
        df["vote_share"].notna() &
        ~df["analysis_level"].isin(["borough_only", "descriptive_only"])
    ].copy()
    derivable["_vs_check"] = derivable["votes"] / derivable["total_valid_votes"] * 100
    h07_mask = (derivable["vote_share"] - derivable["_vs_check"]).abs() > 0.01
    h07 = h07_mask.sum()
    add_result("H07", "HARD",
               "vote_share differs from votes/total_valid_votes by >0.01pp", h07, len(derivable))
    if h07 > 0:
        print("    Sample mismatches:")
        print(derivable[h07_mask][["election_year","authority_name","ward_name_clean",
                                     "votes","total_valid_votes","vote_share","_vs_check"]].head(5))

    # H08
    active_key = ["election_year","authority_code","ward_code",
                  "party_standardised","candidate_name"]
    dupes = active[active.duplicated(subset=active_key, keep=False)]
    h08 = len(dupes)
    add_result("H08", "HARD",
               "Duplicate active ward-party-year-candidate rows", h08, len(active))
    if h08 > 0:
        print("    Sample duplicates:")
        print(dupes[active_key + ["source_dataset"]].head(10))

    # H09
    non_nullable = ["election_year","election_date","source_dataset","data_source_era",
                    "authority_code","authority_name","authority_type","region","tier",
                    "ward_name_raw","ward_name_clean","candidate_name","party_raw",
                    "party_standardised","party_group","is_ilp","elected",
                    "seats_contested","seats_won","analysis_level","harmonisation_status"]
    for col in non_nullable:
        n_null = df[col].isna().sum()
        if n_null > 0:
            add_result(f"H09_{col}", "HARD", f"Non-nullable field '{col}' is null", n_null, denom_all)

    print("\n── EXPECTED ANOMALY CHECKS (WARN) ──")
    # W01
    w01_rows = df[df["turnout_pct"].notna() & (df["turnout_pct"] > 100)]
    w01_unflagged = w01_rows[~w01_rows["notes"].str.contains("turnout_over_100", na=False)]
    add_result("W01", "HARD" if len(w01_unflagged) > 0 else "WARN",
               "Turnout >100 not flagged in notes", len(w01_unflagged), len(w01_rows),
               notes="All turnout >100 rows must carry the flag — unflagged = HARD")

    # W02
    ELEC_NULL_CEILING = {2014: 0.10, 2015: 0.12, 2016: 0.12, 2018: 0.12, 2022: 0.10}
    for yr, ceiling in ELEC_NULL_CEILING.items():
        subset = df[df["election_year"] == yr]
        null_rate = subset["electorate"].isna().mean()
        n_null = subset["electorate"].isna().sum()
        status_type = "WARN" if null_rate <= ceiling else "HARD"
        add_result(f"W02_{yr}", status_type,
                   f"Electorate null rate {yr} (ceiling {ceiling*100:.0f}%)",
                   n_null, len(subset), threshold_pct=ceiling * 100,
                   notes=f"Actual: {null_rate*100:.1f}%.")

    # W03
    uncontested = df[df["notes"].str.contains("uncontested", na=False)]
    add_result("W03", "INFO",
               "Uncontested wards (expect ~157, predominantly 2015)",
               len(uncontested), denom_all,
               notes=f"Year breakdown: {dict(uncontested['election_year'].value_counts().sort_index())}")

    # W04
    yr2016 = df[df["election_year"] == 2016]
    w04 = yr2016["ward_code"].isna().sum()
    add_result("W04", "WARN",
               "Null ward_code in 2016 (expect ~0.2%)",
               w04, len(yr2016), threshold_pct=1.0,
               notes="Known GSS gap in DCLEAPIL 2016. All null-ward rows should be borough_only.")

    # W05
    turnout_null = df["turnout_pct"].isna().sum()
    elec_null = df["electorate"].isna().sum()
    add_result("W05", "INFO",
               "Null turnout_pct rows (expected where electorate is null)",
               turnout_null, denom_all,
               notes=f"Electorate null: {elec_null}. Turnout null should be >= electorate null.")

    # W06
    vs_null = df["vote_share"].isna()
    vs_null_unexpected = df[vs_null & ~df["analysis_level"].isin(["borough_only", "descriptive_only"])]
    add_result("W06", "HARD" if len(vs_null_unexpected) > 0 else "WARN",
               "vote_share null outside borough_only/descriptive_only",
               len(vs_null_unexpected), vs_null.sum())

    print("\n── ENP / FI CROSS-CHECK ──")
    try:
        dcl_raw = pd.read_parquet("data/interim/dcleapil_interim.parquet")
        if "ENP" not in dcl_raw.columns:
            add_result("E01", "INFO",
                       "ENP cross-check skipped — column not in interim file",
                       0, 1,
                       notes="Retain ENP in interim parquet for this check")
        else:
            sample = dcl_raw[
                (dcl_raw["election_year"] == 2022) &
                dcl_raw["ENP"].notna() &
                (dcl_raw["seats_contested"] == 1)
            ].copy()
            sample = sample[sample["authority_name_raw"] != "City of London"]
            mismatches: list[dict[str, object]] = []
            from civic_lens.metrics import fragmentation_index

            for (auth, ward, yr), grp in sample.groupby(["authority_name_raw","ward_code","election_year"]):
                if grp["vote_share"].isna().any():
                    continue
                try:
                    fi = fragmentation_index(dict(zip(grp["candidate_name"], grp["vote_share"])))
                except (ValueError, ZeroDivisionError):
                    continue
                enp = grp["ENP"].iloc[0]
                if abs(fi - enp) > 0.1:
                    mismatches.append({
                        "authority": auth,
                        "ward": ward,
                        "year": yr,
                        "fi_derived": fi,
                        "enp_raw": enp,
                    })
            add_result("E01", "WARN" if len(mismatches) > 0 else "INFO",
                       "ENP vs derived FI mismatches >0.1 in spot-check",
                       len(mismatches), len(sample),
                       notes=f"Spot-check on 2022 single-member wards. {len(mismatches)} diverge.")
            if mismatches:
                print("    Sample mismatches:")
                for m in mismatches[:5]:
                    print(f"      {m}")
    except FileNotFoundError:
        add_result("E01", "INFO",
                   "ENP cross-check skipped — interim parquet not found",
                   0, 1)

    print("\n── CROSS-SOURCE VALIDATION: DCLEAPIL 2022 vs COMMONS 2022 ──")
    commons_active = commons22.copy()
    dcl_superseded = dcl_2022[dcl_2022["notes"].str.contains("superseded_by_commons_2022", na=False)].copy()
    print(f"  Commons 2022 active rows:       {len(commons_active):,}")
    print(f"  DCLEAPIL 2022 superseded rows:  {len(dcl_superseded):,}")

    commons_key = commons_active[["authority_code","ward_name_clean","party_standardised",
                                  "votes","total_valid_votes"]].copy()
    dcl_key = dcl_superseded[["authority_code","ward_name_clean","party_standardised",
                               "votes","total_valid_votes"]].copy()
    merged = commons_key.merge(
        dcl_key.rename(columns={"votes": "dcl_votes",
                                 "total_valid_votes": "dcl_total_valid"}),
        on=["authority_code","ward_name_clean","party_standardised"],
        how="inner"
    )
    print(f"  Matched rows (same authority+ward+party): {len(merged):,}")

    if len(merged) > 0:
        merged["votes_diff"] = (merged["votes"] - merged["dcl_votes"]).abs()
        merged["pct_diff"] = merged["votes_diff"] / merged["total_valid_votes"] * 100
        material_mask = merged["pct_diff"] > 1.0
        material = merged[material_mask]
        add_result("C01", "WARN",
                   "Vote count discrepancy >1% between DCLEAPIL and Commons 2022",
                   len(material), len(merged),
                   notes="Material = |votes_diff| > 1% of total_valid_votes. Log to phase8_conflict_log.csv")
        if len(material) > 0:
            conflict_path = data_root / "phase8_conflict_log.csv"
            material.to_csv(conflict_path, index=False)
            print(f"  Conflict log written: {len(material)} rows")
            print("  Top discrepancies:")
            print(material.nlargest(10, "pct_diff")[
                ["authority_code","ward_name_clean","party_standardised",
                 "votes","dcl_votes","pct_diff"]
            ].to_string(index=False))
        else:
            print("  ✓ No material vote count discrepancies found")

    commons_auth_names = commons_active.groupby("authority_code")["authority_name"].first()
    dcl_auth_names = dcl.groupby("authority_code")["authority_name"].first()
    name_conflicts = {
        code: (commons_auth_names[code], dcl_auth_names[code])
        for code in commons_auth_names.index if code in dcl_auth_names.index and commons_auth_names[code] != dcl_auth_names[code]
    }
    add_result("C02", "WARN" if name_conflicts else "INFO",
               "Authority name disagreement between sources",
               len(name_conflicts), len(commons_auth_names),
               notes=str(name_conflicts) if name_conflicts else "All names consistent")

    commons_wards = set(zip(commons_active["authority_code"], commons_active["ward_name_clean"]))
    dcl_wards_2022 = set(zip(dcl_superseded["authority_code"], dcl_superseded["ward_name_clean"]))
    only_commons = commons_wards - dcl_wards_2022
    only_dcl = dcl_wards_2022 - commons_wards
    add_result("C03", "WARN" if len(only_commons) > 5 else "INFO",
               "Ward names in Commons 2022 not matched in DCLEAPIL 2022",
               len(only_commons), len(commons_wards),
               notes="Small mismatch expected from ward naming convention differences")
    add_result("C04", "INFO",
               "Ward names in DCLEAPIL 2022 not matched in Commons 2022",
               len(only_dcl), len(dcl_wards_2022))

    print("\n── SCOPE-LOCK TRIGGER CHECK ──")
    hard_failures = [r for r in RESULTS if r["check_type"] == "HARD" and r["status"] == "FAIL"]
    total_hard = sum(r["n_affected"] for r in hard_failures)
    n_active = len(active)
    trigger_pct = (total_hard / n_active * 100) if n_active > 0 else 0.0
    add_result("T01", "HARD" if trigger_pct > 5 else "INFO",
               "Scope-lock trigger: hard failures as % of active rows",
               total_hard, n_active, threshold_pct=5.0,
               notes=f"Trigger fires at >5%. Current: {trigger_pct:.2f}%")
    if trigger_pct > 5:
        print(f"\n  ⚠  PIPELINE HOLD: {trigger_pct:.2f}% of active rows have hard failures")
        print(f"     Failing checks: {[r['check_id'] for r in hard_failures]}")
        print("     Document in DECISIONS_LOG.md and resolve before Phase 9.")
    else:
        print(f"\n  ✓  Scope-lock trigger not breached ({trigger_pct:.2f}% < 5%)")

    print("\n── MANCHESTER / NEWCASTLE / LEEDS 2018 SPOT-CHECK ──")
    HIGH_NULL_2018 = {
        "Manchester": {"null_ceiling": 0.0},
        "Newcastle": {"null_ceiling": 0.0},
        "Leeds": {"null_ceiling": 0.0},
    }
    for name, cfg in HIGH_NULL_2018.items():
        sub = df[(df["election_year"] == 2018) &
                 df["authority_name"].str.contains(name, case=False, na=False) &
                 df["votes"].notna() &
                 df["total_valid_votes"].notna()]
        null_vs = sub["vote_share"].isna().sum()
        add_result(
            f"S01_{name.lower()}", "HARD" if null_vs > 0 else "INFO",
            f"{name} 2018: null vote_share where votes present (expect 0 after derivation)",
            null_vs, len(sub),
            notes="Raw DCLEAPIL had 52–58% null; must be 0 after derivation.")
        if len(sub) > 0:
            sample = sub[sub["vote_share"].notna()].head(5)
            for _, row in sample.iterrows():
                expected = row["votes"] / row["total_valid_votes"] * 100
                if abs(row["vote_share"] - expected) > 0.01:
                    print(f"    ⚠ Derivation mismatch: {row['ward_name_clean']} "
                          f"expected {expected:.3f} got {row['vote_share']:.3f}")

    print("\n── WRITING QA REPORT ──")
    qa_path = data_root / "qa_report.csv"
    pd.DataFrame(RESULTS).to_csv(qa_path, index=False)
    print(f"  Wrote {len(RESULTS)} checks to {qa_path}")

    qa_df = pd.DataFrame(RESULTS)
    print("\n── QA SUMMARY ──")
    for status in ["FAIL", "WARN", "PASS", "INFO"]:
        count = (qa_df["status"] == status).sum()
        print(f"  {status}: {count}")

    failing = qa_df[qa_df["status"] == "FAIL"]
    if len(failing) > 0:
        print(f"\n  ⚠  {len(failing)} FAILING checks — pipeline holds:")
        for _, row in failing.iterrows():
            print(f"     [{row['check_id']}] {row['description']}: {row['n_affected']:,} rows")
        print("\n  Document each failure in docs/DECISIONS_LOG.md before proceeding.")
    else:
        print("\n  ✓ No hard failures. Safe to proceed to Phase 9.")
        print("  Document any WARN items in DECISIONS_LOG.md if not already recorded.")


def ensure_directories() -> None:
    data_root = Path("data/processed")
    data_root.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
    main()
