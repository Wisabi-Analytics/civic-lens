from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CLEAN_PATH = Path("data/processed/clean_election_results.csv")
CONCORDANCE_PATH = Path("data/processed/concordance_table.csv")

ALL_OUT_2026_CODES = {
    "E08000016",
    "E08000025",
    "E08000013",
    "E08000033",
    "E08000026",
    "E08000034",
}

MANUAL_MID_WINDOW_ALLOUTS = {
    "E08000035": [2018],
}


def load_results() -> pd.DataFrame:
    df = pd.read_csv(CLEAN_PATH, low_memory=False)
    return df


def detect_mid_window_allouts(df: pd.DataFrame) -> Dict[str, list[int]]:
    suspects: Dict[str, list[int]] = {}
    patrons = df[df["source_dataset"].str.startswith("dcleapil", na=False)]
    for authority_code, grp in patrons.groupby("authority_code"):
        total_wards = grp["ward_code"].nunique()
        if total_wards == 0 or pd.isna(authority_code):
            continue

        ward_per_year = (
            grp[grp["election_year"] <= 2018]
            .groupby("election_year")["ward_code"]
            .nunique()
            .reset_index(name="n_wards")
        )

        suspect_years = (
            ward_per_year[ward_per_year["n_wards"] / total_wards > 0.6]["election_year"].tolist()
        )
        if suspect_years:
            suspects[authority_code] = suspect_years

    LOGGER.info("Detected %s suspected mid-window all-out boroughs", len(suspects))
    return suspects


TRAINING_YEARS = {2014, 2015, 2016}
BACKTEST_YEAR = 2018
TARGET_YEAR = 2022


def build_ward_universe(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dcl = df[
        df["ward_code"].notna() &
        df["source_dataset"].str.startswith("dcleapil", na=False)
    ].copy()

    ward_years = (
        dcl.groupby([
            "authority_code", "authority_name", "ward_code",
            "ward_code_vintage", "ward_name_clean"
        ], dropna=False)
        .agg(years_present=("election_year", lambda x: frozenset(int(y) for y in x.unique() if not pd.isna(y))))
        .reset_index()
    )

    def classify(years: frozenset) -> str:
        has_training = bool(years & TRAINING_YEARS)
        has_2018 = BACKTEST_YEAR in years
        has_2022 = TARGET_YEAR in years
        if has_training and has_2018:
            return "eligible"
        if has_2018 and not has_training:
            return "2018_only"
        if has_2022 and not has_training and not has_2018:
            return "2022_only"
        if has_training and not has_2018:
            return "training_only"
        return "other"

    ward_years["eligibility"] = ward_years["years_present"].apply(classify)

    commons_wards = (
        df[(df["source_dataset"] == "commons_2022") & df["ward_code"].notna()]
        [["authority_code", "authority_name", "ward_code", "ward_name_clean"]]
        .drop_duplicates()
        .assign(
            ward_code_vintage="WD22CD",
            years_present=lambda d: d.apply(lambda _: frozenset([TARGET_YEAR]), axis=1),
            eligibility="2022_only"
        )
    )

    universe_eligible = ward_years[ward_years["eligibility"] == "eligible"].copy()
    universe_2018_only = ward_years[ward_years["eligibility"] == "2018_only"].copy()
    universe_training_only = ward_years[ward_years["eligibility"] == "training_only"].copy()

    universe_2022 = pd.concat([
        ward_years[
            ward_years["eligibility"].isin({"eligible", "2022_only"}) &
            (ward_years["ward_code_vintage"] == "WD22CD")
        ],
        commons_wards
    ], ignore_index=True).drop_duplicates(subset=["authority_code", "ward_code"])

    LOGGER.info("Ward universe: %s eligible, %s 2018-only, %s training-only, %s 2022 rows",
                len(universe_eligible), len(universe_2018_only), len(universe_training_only), len(universe_2022))
    LOGGER.info("Fallback denominator = %s eligible wards", len(universe_eligible))
    return universe_eligible, universe_2018_only, universe_2022, universe_training_only

    # Not returned: universe_training_only already above


def match_layer1_exact_code(universe_18: pd.DataFrame, mid_window_allouts: dict) -> pd.DataFrame:
    has_training = universe_18["years_present"].apply(
        lambda years: any(year in [2014, 2015, 2016] for year in years)
    )
    has_2018 = universe_18["years_present"].apply(lambda years: 2018 in years)
    stable = universe_18[has_training & has_2018].copy()
    stable = stable[~stable["authority_code"].isin(mid_window_allouts.keys())]

    stable = stable.assign(
        ward_code_training=stable["ward_code"],
        ward_code_2018=stable["ward_code"],
        ward_code_2022=pd.NA,
        match_method="exact_code",
        confidence="high",
        change_type=pd.NA,
        analysis_level=pd.NA,
        fallback_reason=pd.NA
    )

    LOGGER.info("Layer 1 exact code matches: %s", len(stable))
    return stable


def match_layer2_name(universe_18: pd.DataFrame, universe_22: pd.DataFrame) -> pd.DataFrame:
    left = universe_18[["authority_code", "authority_name", "ward_code", "ward_name_clean"]]
    right = universe_22[["authority_code", "ward_code", "ward_name_clean"]].rename(
        columns={"ward_code": "ward_code_2022"}
    )
    matched = left.merge(right, on=["authority_code", "ward_name_clean"], how="inner")
    code_match = matched["ward_code"] == matched["ward_code_2022"]
    name_only = matched[~code_match].copy()

    name_only = name_only.assign(
        ward_code_training=name_only["ward_code"],
        ward_code_2018=name_only["ward_code"],
        match_method="name_matched",
        confidence="medium",
        change_type=pd.NA,
        analysis_level=pd.NA,
        fallback_reason=pd.NA
    )

    LOGGER.info("Layer 2 name matches: %s", len(name_only))
    return name_only


def detect_splits_merges(universe_18: pd.DataFrame, universe_22: pd.DataFrame) -> pd.DataFrame:
    xwalk = pd.read_parquet("data/interim/ward_lad_dec2011.parquet")
    link = universe_18.merge(
        xwalk[["WD11CD", "WD22CD"]].rename(
            columns={"WD11CD": "ward_code", "WD22CD": "ward_code_2022_xwalk"}
        ),
        on="ward_code",
        how="left"
    )

    code_counts_22 = (
        xwalk.groupby("WD11CD")["WD22CD"].nunique().reset_index(name="n_successors")
    )
    code_counts_11 = (
        xwalk.groupby("WD22CD")["WD11CD"].nunique().reset_index(name="n_predecessors")
    )

    link = link.merge(
        code_counts_22.rename(columns={"WD11CD": "ward_code"}),
        on="ward_code",
        how="left"
    )
    link = link.merge(
        code_counts_11.rename(columns={"WD22CD": "ward_code_2022_xwalk"}),
        on="ward_code_2022_xwalk",
        how="left"
    )

    def classify(row):
        if pd.isna(row.get("ward_code_2022_xwalk")):
            return "unmatched"
        n_succ = row.get("n_successors", 1)
        n_pred = row.get("n_predecessors", 1)
        if n_succ > 1:
            return "split"
        if n_pred > 1:
            return "merge"
        return "stable"

    link["change_type_xwalk"] = link.apply(classify, axis=1)
    splits_merges = link[link["change_type_xwalk"].isin(["split", "merge"])].copy()

    splits_merges = splits_merges.assign(
        ward_code_training=splits_merges["ward_code"],
        ward_code_2018=splits_merges["ward_code"],
        ward_code_2022=splits_merges["ward_code_2022_xwalk"],
        match_method="reviewed",
        confidence="low",
        analysis_level="borough_fallback",
        fallback_reason=splits_merges["change_type_xwalk"].map(lambda t: f"Boundary change: {t}")
    )

    LOGGER.info("Layer 3 split/merge detections: %s", len(splits_merges))
    return splits_merges


def add_borough_fallbacks(concordance: pd.DataFrame,
                           eligible_18: pd.DataFrame,
                           eligible_22: pd.DataFrame) -> pd.DataFrame:
    matched_18 = set(zip(concordance["authority_code"], concordance["ward_code_training"].dropna()))
    matched_22 = set(zip(concordance["authority_code"], concordance["ward_code_2022"].dropna()))

    fallback_rows = []
    for _, row in eligible_18.iterrows():
        key = (row["authority_code"], row["ward_code"])
        if key in matched_18:
            continue
        fallback_rows.append({
            "authority_code": row["authority_code"],
            "authority_name": row["authority_name"],
            "ward_code_training": row["ward_code"],
            "ward_code_2018": row["ward_code"],
            "ward_code_2022": pd.NA,
            "ward_name_clean": row["ward_name_clean"],
            "match_method": "borough_fallback",
            "confidence": "low",
            "change_type": "unmatched",
            "analysis_level": "borough_only",
            "fallback_reason": "No match found across vintage transition",
        })

    for _, row in eligible_22.iterrows():
        key = (row["authority_code"], row["ward_code"])
        if key in matched_22:
            continue
        fallback_rows.append({
            "authority_code": row["authority_code"],
            "authority_name": row["authority_name"],
            "ward_code_training": pd.NA,
            "ward_code_2018": pd.NA,
            "ward_code_2022": row["ward_code"],
            "ward_name_clean": row["ward_name_clean"],
            "match_method": "borough_fallback",
            "confidence": "low",
            "change_type": "unmatched",
            "analysis_level": "borough_only",
            "fallback_reason": "New ward in 2022 with no matched predecessor",
        })

    if fallback_rows:
        concordance = pd.concat([concordance, pd.DataFrame(fallback_rows)], ignore_index=True)
    LOGGER.info("After fallback: %s rows", len(concordance))
    return concordance


def finalise_concordance(concordance: pd.DataFrame,
                          mid_window_allouts: dict,
                          all_out_2026_codes: set) -> pd.DataFrame:
    for code, years in mid_window_allouts.items():
        mask = concordance["authority_code"] == code
        concordance.loc[mask, "change_type"] = "all_out_lgbce"
        concordance.loc[mask, "analysis_level"] = "borough_only"
        concordance.loc[mask, "fallback_reason"] = (
            f"Mid-window LGBCE all-out election in {years} broke ward chain"
        )
        concordance.loc[mask, "confidence"] = "low"

    stable_mask = (concordance["match_method"] == "exact_code") & concordance["change_type"].isna()
    concordance.loc[stable_mask, "change_type"] = "stable"
    concordance.loc[stable_mask, "analysis_level"] = "ward"

    name_mask = (concordance["match_method"] == "name_matched") & concordance["change_type"].isna()
    concordance.loc[name_mask, "change_type"] = "stable"
    concordance.loc[name_mask, "analysis_level"] = "ward"

    all_out_mask = concordance["authority_code"].isin(all_out_2026_codes)
    concordance.loc[all_out_mask, "change_type"] = "all_out_lgbce"

    concordance["analysis_level"] = concordance["analysis_level"].fillna("borough_only")
    concordance["change_type"] = concordance["change_type"].fillna("unmatched")
    return concordance


def build_concordance_table(df: pd.DataFrame,
                            universe_eligible: pd.DataFrame,
                            universe_2018_only: pd.DataFrame,
                            universe_2022: pd.DataFrame,
                            universe_training_only: pd.DataFrame,
                            mid_window_allouts: dict) -> pd.DataFrame:
    eligible_18 = universe_eligible[universe_eligible["ward_code_vintage"] == "WD18CD"].copy()
    eligible_22 = universe_eligible[universe_eligible["ward_code_vintage"] == "WD22CD"].copy()

    l1 = match_layer1_exact_code(eligible_18, mid_window_allouts)
    l2 = match_layer2_name(eligible_18, universe_2022)
    l3 = detect_splits_merges(eligible_18, universe_2022)

    concordance = pd.concat([l1, l2, l3], ignore_index=True, sort=False)
    concordance = add_borough_fallbacks(concordance, eligible_18, eligible_22)

    for _, row in universe_2018_only.iterrows():
        concordance = pd.concat([
            concordance,
            pd.DataFrame([{"authority_code": row["authority_code"],
                           "authority_name": row.get("authority_name", ""),
                           "ward_code_training": pd.NA,
                           "ward_code_2018": row["ward_code"],
                           "ward_code_2022": pd.NA,
                           "ward_name_clean": row["ward_name_clean"],
                           "match_method": "uncalibrated",
                           "confidence": "low",
                           "change_type": "uncalibrated",
                           "analysis_level": "borough_only",
                           "fallback_reason": "By-thirds ward: no elections in training window (2014–2016)",
                        }])], ignore_index=True)

    for _, row in universe_training_only.iterrows():
        concordance = pd.concat([
            concordance,
            pd.DataFrame([{"authority_code": row["authority_code"],
                           "authority_name": row.get("authority_name", ""),
                           "ward_code_training": row["ward_code"],
                           "ward_code_2018": pd.NA,
                           "ward_code_2022": pd.NA,
                           "ward_name_clean": row["ward_name_clean"],
                           "match_method": "uncalibrated",
                           "confidence": "low",
                           "change_type": "unmatched",
                           "analysis_level": "borough_only",
                           "fallback_reason": "Ward retired before 2018 — boundary change removed it",
                        }])], ignore_index=True)

    uncalibrated_22 = universe_2022[universe_2022["eligibility"] == "2022_only"].copy()
    for _, row in uncalibrated_22.iterrows():
        concordance = pd.concat([
            concordance,
            pd.DataFrame([{"authority_code": row["authority_code"],
                           "authority_name": row.get("authority_name", ""),
                           "ward_code_training": pd.NA,
                           "ward_code_2018": pd.NA,
                           "ward_code_2022": row["ward_code"],
                           "ward_name_clean": row["ward_name_clean"],
                           "match_method": "uncalibrated",
                           "confidence": "low",
                           "change_type": "uncalibrated",
                           "analysis_level": "borough_only",
                           "fallback_reason": "New ward in 2022 with no matched predecessor",
                        }])], ignore_index=True)
    priority = {"exact_code": 1, "name_matched": 2, "reviewed": 3, "borough_fallback": 4, "uncalibrated": 5}
    concordance["_priority"] = concordance["match_method"].map(priority).fillna(99)
    training_rows = (
        concordance[concordance["ward_code_training"].notna()]
        .sort_values(["_priority", "authority_code"])
        .drop_duplicates(subset=["authority_code", "ward_code_training"], keep="first")
    )
    post_rows = (
        concordance[concordance["ward_code_training"].isna()]
        .sort_values(["_priority", "authority_code"])
        .drop_duplicates(subset=["authority_code", "ward_code_2022"], keep="first")
    )
    concordance = pd.concat([training_rows, post_rows], ignore_index=True)
    concordance = concordance.drop(columns=["_priority"]).reset_index(drop=True)
    concordance = finalise_concordance(concordance, mid_window_allouts, ALL_OUT_2026_CODES)
    return concordance


def write_concordance(concordance: pd.DataFrame) -> None:
    cols = [
        "authority_code", "authority_name", "ward_code_training",
        "ward_code_2018", "ward_code_2022", "ward_name_clean",
        "match_method", "confidence", "change_type",
        "analysis_level", "fallback_reason",
    ]
    concordance[cols].to_csv(CONCORDANCE_PATH, index=False, encoding="utf-8")
    LOGGER.info("Concordance table written: %s rows", len(concordance))


def update_results_from_concordance(df: pd.DataFrame, concordance: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    method_to_status = {
        "exact_code": "matched",
        "name_matched": "name_matched",
        "reviewed": "reviewed",
        "borough_fallback": "fallback",
        "uncalibrated": "fallback",
    }

    conc_18 = concordance[concordance["ward_code_2018"].notna()][[
        "authority_code", "ward_code_2018", "match_method", "change_type", "analysis_level"
    ]].rename(columns={
        "ward_code_2018": "ward_code",
        "match_method": "_match_method",
        "change_type": "_change_type",
        "analysis_level": "_analysis_level",
    })

    mask_18 = df["ward_code_vintage"] == "WD18CD"
    df_18 = df[mask_18].merge(conc_18, on=["authority_code", "ward_code"], how="left")
    df_18["harmonisation_status"] = df_18["_match_method"].map(method_to_status).fillna("fallback")
    df_18["concordance_change_type"] = df_18["_change_type"].fillna("unmatched")
    upgrade_18 = (df_18["analysis_level"] != "descriptive_only") & df_18["_analysis_level"].notna()
    df_18.loc[upgrade_18, "analysis_level"] = df_18.loc[upgrade_18, "_analysis_level"]
    df_18 = df_18.drop(columns=["_match_method", "_change_type", "_analysis_level"])

    conc_22 = concordance[concordance["ward_code_2022"].notna()][[
        "authority_code", "ward_code_2022", "match_method", "change_type", "analysis_level"
    ]].rename(columns={
        "ward_code_2022": "ward_code",
        "match_method": "_match_method",
        "change_type": "_change_type",
        "analysis_level": "_analysis_level",
    })
    if not conc_22.empty:
        priority = {"exact_code": 1, "name_matched": 2, "reviewed": 3, "borough_fallback": 4}
        conc_22["_priority"] = conc_22["_match_method"].map(priority).fillna(99)
        conc_22 = (
            conc_22.sort_values(["_priority", "authority_code"], kind="stable")
            .drop_duplicates(subset=["authority_code", "ward_code"], keep="first")
        )
        conc_22 = conc_22.drop(columns=["_priority"])

    mask_22 = df["ward_code_vintage"] == "WD22CD"
    df_22 = df[mask_22].merge(conc_22, on=["authority_code", "ward_code"], how="left")
    df_22["harmonisation_status"] = df_22["_match_method"].map(method_to_status).fillna("fallback")
    df_22["concordance_change_type"] = df_22["_change_type"].fillna("unmatched")
    upgrade_22 = (df_22["analysis_level"] != "descriptive_only") & df_22["_analysis_level"].notna()
    df_22.loc[upgrade_22, "analysis_level"] = df_22.loc[upgrade_22, "_analysis_level"]
    df_22 = df_22.drop(columns=["_match_method", "_change_type", "_analysis_level"])

    mask_null = df["ward_code"].isna()
    df_null = df[mask_null].copy()
    df_null["harmonisation_status"] = "fallback"
    df_null["concordance_change_type"] = "unmatched"

    result = pd.concat([df_18, df_22, df_null], ignore_index=True)
    assert len(result) == len(df), "Row count changed during concordance writeback"
    return result


def main() -> None:
    LOGGER.info("Phase 7 concordance starting")
    df = load_results()
    detected_allouts = detect_mid_window_allouts(df)
    universe_eligible, universe_2018_only, universe_2022, universe_training_only = build_ward_universe(df)
    mid_window_allouts = MANUAL_MID_WINDOW_ALLOUTS or detected_allouts
    concordance = build_concordance_table(
        df,
        universe_eligible,
        universe_2018_only,
        universe_2022,
        universe_training_only,
        mid_window_allouts,
    )
    write_concordance(concordance)
    updated = update_results_from_concordance(df, concordance)
    updated.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    LOGGER.info("Concordance writeback complete: %s rows", len(updated))


if __name__ == "__main__":
    main()
