from __future__ import annotations

from pathlib import Path
import logging

import pandas as pd

from civic_lens.ward_name_utils import clean_ward_name

LOGGER = logging.getLogger(__name__)

INTERIM_DIR = Path("data/interim")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(exist_ok=True)

CANONICAL_COLS = [
    "election_year",
    "election_date",
    "source_dataset",
    "data_source_era",
    "authority_code",
    "authority_name",
    "authority_type",
    "region",
    "tier",
    "ward_name_raw",
    "ward_name_clean",
    "ward_code",
    "ward_code_vintage",
    "candidate_name",
    "party_raw",
    "party_id",
    "party_standardised",
    "party_group",
    "is_ilp",
    "votes",
    "vote_share",
    "total_valid_votes",
    "elected",
    "seats_contested",
    "seats_won",
    "electorate",
    "turnout_pct",
    "analysis_level",
    "harmonisation_status",
    "concordance_change_type",
    "notes",
]

ELECTION_DATES = {
    2014: "2014-05-22",
    2015: "2015-05-07",
    2016: "2016-05-05",
    2018: "2018-05-03",
    2022: "2022-05-05",
}

MANUAL_PARTY_MAP = {
    "NR_Ind":            ("IND",       "Independent", False),
    "NR_IndLR":          ("IND",       "Independent", False),
    "joint-party:15-64": ("IND_LOCAL", "ILP",         True),
}

PARTY_RAW_FALLBACK = {
    "CON": ("Conservative And Unionist Party", "Major", False),
    "CONSERVATIVE": ("Conservative And Unionist Party", "Major", False),
    "LAB": ("Labour And Cooperative Party", "Major", False),
    "LABOUR": ("Labour And Cooperative Party", "Major", False),
    "LD": ("Liberal Democrats", "Major", False),
    "LIB": ("Liberal Democrats", "Major", False),
    "LIBERAL": ("Liberal Democrats", "Major", False),
    "GREEN": ("Green Party", "Minor", False),
    "GREENS": ("Green Party", "Minor", False),
    "PC": ("Plaid Cymru", "Minor", False),
    "PLAID": ("Plaid Cymru", "Minor", False),
    "UKIP": ("Reform Uk", "Minor", False),
    "REF": ("Reform Uk", "Minor", False),
    "YORKS": ("Yorkshire Party", "Minor", False),
    "YORKSHIRE": ("Yorkshire Party", "Minor", False),
    "VOLT": ("Volt United Kingdom", "Minor", False),
    "TUSC": ("Trade Unionist And Socialist Coalition", "Minor", False),
    "SOC": ("Social Democratic Party", "Minor", False),
    "BRFIRST": ("Britain First", "Minor", False),
    "BRITF": ("Britain First", "Minor", False),
}


def _append_note(series: pd.Series, flag: str) -> pd.Series:
    return series.where(series.isna(), series + " | " + flag).fillna(flag)


def load_party_lookup() -> pd.DataFrame:
    party_path = INTERIM_DIR / "party_coding.parquet"
    party = pd.read_parquet(party_path)
    party = party.rename(columns={"party_id_key": "party_id"})
    party["party_id"] = party["party_id"].astype("string")
    return party


def _standardize_party(df: pd.DataFrame, party_lookup: pd.DataFrame) -> pd.DataFrame:
    merged = df.copy()
    party_ids = merged["party_id"].astype("string")
    can_merge = party_ids.str.startswith("PP")
    merge_frame = merged.copy()
    merge_frame.loc[~can_merge, "party_id"] = pd.NA
    merged = merge_frame.merge(party_lookup, on="party_id", how="left")
    merged["party_id"] = party_ids

    for pid, (std, grp, ilp) in MANUAL_PARTY_MAP.items():
        mask = merged["party_id"] == pid
        merged.loc[mask, "party_standardised"] = std
        merged.loc[mask, "party_group"] = grp
        merged.loc[mask, "is_ilp"] = ilp

    raw_upper = merged["party_raw"].fillna("").str.upper().str.strip()

    for raw_key, (std, grp, ilp) in PARTY_RAW_FALLBACK.items():
        raw_mask = raw_upper == raw_key
        mask = merged["party_standardised"].isna() & raw_mask
        merged.loc[mask, "party_standardised"] = std
        merged.loc[mask, "party_group"] = grp
        merged.loc[mask, "is_ilp"] = ilp

    no_party_id = merged["party_id"].isna()
    if no_party_id.any():
        ind_mask = no_party_id | merged["party_raw"].str.upper().str.contains("INDEPENDENT", na=False)
        merged.loc[ind_mask, "party_standardised"] = merged.loc[ind_mask, "party_standardised"].fillna("IND")
        merged.loc[ind_mask, "party_group"] = merged.loc[ind_mask, "party_group"].fillna("Independent")
        merged.loc[ind_mask, "is_ilp"] = merged.loc[ind_mask, "is_ilp"].fillna(False)

    unresolved = merged["party_standardised"].isna()
    if unresolved.any():
        merged.loc[unresolved, "party_standardised"] = "UNKNOWN"
        merged.loc[unresolved, "party_group"] = merged.loc[unresolved, "party_group"].fillna("Unknown")
        merged.loc[unresolved, "is_ilp"] = merged.loc[unresolved, "is_ilp"].fillna(False)
        LOGGER.warning("Filled %s unresolved party_id rows with UNKNOWN", unresolved.sum())

    merged["is_ilp"] = merged["is_ilp"].fillna(False).astype(bool)
    merged["party_group"] = merged["party_group"].replace("Not categorised", "Unknown")
    return merged


def build_dcleapil_canonical(party_lookup: pd.DataFrame) -> pd.DataFrame:
    path = INTERIM_DIR / "dcleapil_interim.parquet"
    df = pd.read_parquet(path)

    df["election_date"] = df["election_year"].map(ELECTION_DATES)
    df["elected"] = df["elected_raw"].map({"t": True, "f": False})
    df["elected"] = df["elected"].fillna(False).astype(bool)
    df["seats_won"] = df["elected"].astype("Int64")
    df["ward_name_clean"] = df["ward_name_raw"].apply(clean_ward_name)
    df = _standardize_party(df, party_lookup)

    for col in ["authority_code", "authority_name", "authority_type", "region", "tier"]:
        df[col] = None

    df["notes"] = None
    df["analysis_level"] = None
    CITY_OF_LONDON_NAME = "City of London"
    col_mask = df["authority_name_raw"] == CITY_OF_LONDON_NAME
    if col_mask.any():
        df.loc[col_mask, "vote_share"] = pd.NA
        df.loc[col_mask, "analysis_level"] = "borough_only"
        df.loc[col_mask, "notes"] = _append_note(
            df.loc[col_mask, "notes"], "city_of_london_block_voting"
        )
        LOGGER.info("City of London rows set to borough_only and vote_share null (block voting)")

    df["harmonisation_status"] = None
    df["concordance_change_type"] = None
    df = df.drop(columns=["elected_raw"], errors="ignore")
    return df


def build_commons_2022_canonical(party_lookup: pd.DataFrame) -> pd.DataFrame:
    cand_path = INTERIM_DIR / "commons_2022_candidates.parquet"
    ward_path = INTERIM_DIR / "commons_2022_wards.parquet"
    cand = pd.read_parquet(cand_path)
    ward = pd.read_parquet(ward_path)

    cand = cand.drop(columns=["County code", "County name"], errors="ignore")

    ward_dedup = (
        ward[["ward_code", "authority_code", "electorate", "turnout_pct", "seats_contested"]]
        .drop_duplicates(subset=["ward_code", "authority_code"])
    )

    merged = cand.merge(
        ward_dedup,
        on=["ward_code", "authority_code"],
        how="left",
        suffixes=("", "_ward"),
    )

    merged["election_date"] = merged["election_date"].dt.strftime("%Y-%m-%d")
    merged["elected"] = merged["elected_raw"].map(
        {"Yes": True, "No": False, 1: True, 0: False, True: True, False: False}
    )
    merged["elected"] = merged["elected"].fillna(False).astype(bool)
    merged["seats_won"] = merged["elected"].astype("Int64")
    merged["ward_name_clean"] = merged["ward_name_raw"].apply(clean_ward_name)
    merged = _standardize_party(merged, party_lookup)

    for col in ["authority_code", "authority_name", "authority_type", "region", "tier"]:
        merged[col] = None

    merged["notes"] = None
    merged["analysis_level"] = None
    merged["harmonisation_status"] = None
    merged["concordance_change_type"] = None
    return merged


def resolve_commons_conflict(
    dcleapil: pd.DataFrame,
    commons: pd.DataFrame,
) -> pd.DataFrame:
    keys = {
        tuple(x)
        for x in commons[["ward_code", "party_standardised"]].dropna().to_records(index=False)
    }

    tuples = [
        (wc, ps)
        for wc, ps in zip(
            dcleapil["ward_code"],
            dcleapil["party_standardised"],
        )
    ]
    mask = (dcleapil["election_year"] == 2022) & pd.Series(tuples).isin(keys)

    dcleapil.loc[mask, "analysis_level"] = "descriptive_only"
    dcleapil.loc[mask, "notes"] = _append_note(
        dcleapil.loc[mask, "notes"], "superseded_by_commons_2022"
    )

    commons_agg = (
        commons.groupby(["ward_code", "party_standardised"], dropna=False)["votes"]
        .sum()
        .reset_index(name="commons_votes")
    )

    conflict = dcleapil.loc[mask, ["ward_code", "party_standardised", "votes"]]
    conflict = conflict.merge(
        commons_agg,
        on=["ward_code", "party_standardised"],
        how="left",
    )
    conflict = conflict[conflict["commons_votes"].notna() & (conflict["commons_votes"] > 0)]
    conflict["pct_difference"] = (
        (conflict["votes"] - conflict["commons_votes"]).abs()
        / conflict["commons_votes"]
    )
    conflict = conflict[conflict["pct_difference"] > 0.01]

    log_path = PROCESSED_DIR / "phase5_conflict_log.csv"
    if not conflict.empty:
        conflict = conflict.rename(
            columns={
                "votes": "dcleapil_votes",
            }
        )[
            [
                "ward_code",
                "party_standardised",
                "dcleapil_votes",
                "commons_votes",
                "pct_difference",
            ]
        ]
        conflict.to_csv(log_path, index=False, encoding="utf-8")
    else:
        if log_path.exists():
            log_path.unlink()

    return dcleapil


def assign_provisional_analysis_level(df: pd.DataFrame) -> pd.DataFrame:
    df["analysis_level"] = df["analysis_level"].fillna("ward")

    ward_candidate_counts = (
        df.groupby(
            ["election_year", "ward_code", "authority_name_raw"], dropna=False
        )
        .size()
        .reset_index(name="n_candidates_in_ward")
    )

    df = df.merge(
        ward_candidate_counts,
        on=["election_year", "ward_code", "authority_name_raw"],
        how="left",
    )

    uncontested_mask = (
        (df["n_candidates_in_ward"] == 1)
        & df["votes"].isna()
    )
    borough_only_mask = df["analysis_level"] != "descriptive_only"
    df.loc[
        uncontested_mask & borough_only_mask,
        "analysis_level",
    ] = "borough_only"

    null_ward_mask = df["ward_code"].isna()
    df.loc[null_ward_mask & (df["analysis_level"] == "ward"), "analysis_level"] = (
        "borough_only"
    )

    over_100_mask = df["turnout_pct"].notna() & (df["turnout_pct"] > 100)
    df.loc[over_100_mask & (df["analysis_level"] == "ward"), "analysis_level"] = (
        "borough_only"
    )

    return df


def assign_notes(df: pd.DataFrame) -> pd.DataFrame:
    multi_mask = df["seats_contested"] > 1
    df.loc[multi_mask, "notes"] = _append_note(
        df.loc[multi_mask, "notes"], "multi_member"
    )

    uncontested_mask = (df["n_candidates_in_ward"] == 1) & df["votes"].isna()
    df.loc[uncontested_mask, "notes"] = _append_note(
        df.loc[uncontested_mask, "notes"], "uncontested"
    )

    has_vs = df["vote_share"].notna()
    df.loc[has_vs, "notes"] = _append_note(
        df.loc[has_vs, "notes"], "vote_share_derived"
    )

    turnout_corrected = (
        df["source_dataset"].str.startswith("dcleapil", na=False)
        & (df["seats_contested"] > 1)
    )
    df.loc[turnout_corrected, "notes"] = _append_note(
        df.loc[turnout_corrected, "notes"], "turnout_corrected"
    )

    elec_null = df["electorate"].isna()
    df.loc[elec_null, "notes"] = _append_note(
        df.loc[elec_null, "notes"], "electorate_missing"
    )

    turn_null = df["turnout_pct"].isna()
    df.loc[turn_null, "notes"] = _append_note(
        df.loc[turn_null, "notes"], "turnout_missing"
    )

    over_100 = df["turnout_pct"].notna() & (df["turnout_pct"] > 100)
    df.loc[over_100, "notes"] = _append_note(
        df.loc[over_100, "notes"], "turnout_over_100_post_correction"
    )

    return df


def set_harmonisation_defaults(df: pd.DataFrame) -> pd.DataFrame:
    df["harmonisation_status"] = "unmatched"
    df["concordance_change_type"] = None
    return df


def _ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in CANONICAL_COLS:
        if col not in df.columns:
            df[col] = None
    return df


def _enforce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    df["election_year"] = df["election_year"].astype("Int64")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").astype("Int64")
    df["total_valid_votes"] = (
        pd.to_numeric(df["total_valid_votes"], errors="coerce").astype("Int64")
    )
    df["electorate"] = pd.to_numeric(df["electorate"], errors="coerce").astype("Int64")
    df["seats_contested"] = (
        pd.to_numeric(df["seats_contested"], errors="coerce").astype("Int64")
    )
    df["seats_won"] = df["seats_won"].astype("Int64")
    df["vote_share"] = pd.to_numeric(df["vote_share"], errors="coerce").astype(float)
    df["turnout_pct"] = pd.to_numeric(df["turnout_pct"], errors="coerce").astype(float)
    df["is_ilp"] = df["is_ilp"].astype(bool)
    df["elected"] = df["elected"].astype(bool)
    return df


def deduplicate_structure(df: pd.DataFrame) -> None:
    active = df[df["analysis_level"] != "descriptive_only"]
    dupe_key = ["election_year", "ward_code", "party_standardised", "candidate_name"]
    dupes = active[active.duplicated(subset=dupe_key, keep=False)]
    if not dupes.empty:
        LOGGER.warning(
            "%s duplicate ward-party-year-candidate rows detected", len(dupes)
        )
        LOGGER.warning(dupes[dupe_key + ["source_dataset", "notes"]].head(20))


def assemble_clean_results():
    party_lookup = load_party_lookup()
    dcleapil = build_dcleapil_canonical(party_lookup)
    commons = build_commons_2022_canonical(party_lookup)
    dcleapil = resolve_commons_conflict(dcleapil, commons)

    combined = pd.concat(
        [
            _ensure_canonical_columns(dcleapil),
            _ensure_canonical_columns(commons),
        ],
        ignore_index=True,
    )

    combined = assign_provisional_analysis_level(combined)
    combined = assign_notes(combined)
    combined = set_harmonisation_defaults(combined)
    combined["seats_contested"] = combined["seats_contested"].clip(upper=3)

    combined = _ensure_canonical_columns(combined)
    combined = combined[CANONICAL_COLS + ["n_candidates_in_ward"]]
    combined = combined.sort_values(
        ["source_dataset", "election_year", "ward_code", "party_standardised"]
    )
    deduplicate_structure(combined)

    combined = _enforce_dtypes(combined)
    combined = combined.drop(columns=["n_candidates_in_ward"])

    (PROCESSED_DIR / "clean_election_results.csv").write_text("")
    combined.to_csv(
        PROCESSED_DIR / "clean_election_results.csv",
        index=False,
        encoding="utf-8",
    )


def main():
    logging.basicConfig(level=logging.INFO)
    LOGGER.info("Phase 5 ingestion starting")
    assemble_clean_results()
    LOGGER.info("Phase 5 ingestion complete")


if __name__ == "__main__":
    main()
