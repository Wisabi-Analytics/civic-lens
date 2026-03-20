from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)

DCLEAPIL_INTERIM_PATH = Path("data/interim/dcleapil_interim.parquet")

CLEAN_PATH = Path("data/processed/clean_election_results.csv")
DIM_PATH = Path("data/processed/authority_dimension.csv")

WEST_YORKSHIRE_CODES = {
    "E08000032",
    "E08000033",
    "E08000034",
    "E08000035",
    "E08000036",
}

EXCLUDED_METRO_CODES = {
    "E08000017",  # Doncaster
    "E08000012",  # Liverpool
    "E08000015",  # Wirral
    "E08000018",  # Rotherham
}

ALLOUT_CODES = {
    "E08000016",  # Barnsley
    "E08000025",  # Birmingham
    "E08000013",  # St Helens
    "E08000033",  # Calderdale
    "E08000026",  # Coventry
    "E08000034",  # Kirklees
}


def load_lookups():
    lad_region = (
        pd.read_parquet("data/interim/lad_region_apr2023.parquet")
        [["LAD23CD", "LAD23NM", "RGN23NM"]]
        .astype({"LAD23CD": "string"})
    )
    wl_18 = pd.read_parquet("data/interim/ward_lad_dec2018.parquet")
    wl_22 = pd.read_parquet("data/interim/ward_lad_dec2022.parquet")
    wl_11 = pd.read_parquet("data/interim/ward_lad_dec2011.parquet")[
        ["WD11CD", "LAD22CD"]
    ]
    return lad_region, wl_18, wl_22, wl_11


def build_ward_authority_lookup() -> pd.Series:
    df = pd.read_parquet(DCLEAPIL_INTERIM_PATH)[["ward_code", "authority_name_raw"]]
    df = df.dropna(subset=["ward_code", "authority_name_raw"])
    df = df.drop_duplicates(subset=["ward_code"])
    return df.set_index("ward_code")["authority_name_raw"]


def join_authority_code_dcleapil(
    df: pd.DataFrame,
    wl_18: pd.DataFrame,
    wl_22: pd.DataFrame,
    lad_region: pd.DataFrame,
    wl_11: pd.DataFrame,
    ward_authority: pd.Series,
) -> pd.DataFrame:
    wl_18 = wl_18[["WD18CD", "LAD18CD"]]
    wl_22 = wl_22[["WD22CD", "LAD22CD"]]

    def _merge_lookup(
        subset: pd.DataFrame,
        lookup: pd.DataFrame,
        ward_col: str,
        lad_col: str,
    ) -> pd.DataFrame:
        temp = subset.copy()
        temp["__orig_index"] = temp.index
        temp = temp.merge(
            lookup,
            left_on="ward_code",
            right_on=ward_col,
            how="left",
        )
        temp = temp.rename(columns={lad_col: "lad_code_from_lookup"})
        return temp.drop(columns=[ward_col], errors="ignore")

    mask_2022 = df["election_year"] == 2022
    pre22 = _merge_lookup(df[~mask_2022], wl_18, "WD18CD", "LAD18CD")
    yr22 = _merge_lookup(df[mask_2022], wl_22, "WD22CD", "LAD22CD")

    dcl = pd.concat([pre22, yr22], axis=0)
    dcl["ward_code"] = dcl["ward_code"].astype("string").str.strip()
    dcl["authority_name_raw"] = dcl["ward_code"].map(ward_authority)

    wl_11_map = (
        wl_11.drop_duplicates(subset=["WD11CD"])
        .set_index("WD11CD")["LAD22CD"]
        .astype("string")
    )
    missing_lookup = dcl["lad_code_from_lookup"].isna() & dcl["ward_code"].notna()
    dcl.loc[missing_lookup, "lad_code_from_lookup"] = (
        dcl.loc[missing_lookup, "ward_code"].map(wl_11_map)
    )

    missing_lookup2 = dcl["lad_code_from_lookup"].isna() & dcl["authority_name_raw"].notna()
    authority_map = (
        lad_region.assign(
            authority_norm=(
                lad_region["LAD23NM"]
                .str.lower()
                .str.replace("&", "and", regex=False)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
        )
        .drop_duplicates(subset=["authority_norm"])
        .set_index("authority_norm")["LAD23CD"]
    )
    if missing_lookup2.any():
        norm_names = (
            dcl.loc[missing_lookup2, "authority_name_raw"]
            .str.lower()
            .str.replace("&", "and", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )
        filled = norm_names.map(authority_map)
        dcl.loc[missing_lookup2, "lad_code_from_lookup"] = filled

    still_missing = dcl["lad_code_from_lookup"].isna()
    if still_missing.any():
        LOGGER.warning(
            "%s DCLEAPIL rows still missing LAD lookup after fallback", still_missing.sum()
        )
        LOGGER.warning(
            "Sample missing wards: %s",
            dcl.loc[still_missing, ["election_year", "ward_code"]]
            .drop_duplicates()
            .head(),
        )

    merged = dcl.merge(
        lad_region,
        left_on="lad_code_from_lookup",
        right_on="LAD23CD",
        how="left",
        suffixes=("", "_lad"),
    )
    merged["authority_code"] = merged["LAD23CD"]
    merged["authority_name"] = merged["LAD23NM"]
    merged["region"] = merged["RGN23NM"]

    missing = merged["authority_code"].isna()
    if missing.any():
        LOGGER.warning(
            "%s DCLEAPIL rows missing authority_code after geography join",
            missing.sum(),
        )
        LOGGER.warning(
            "Sample missing: %s",
            merged.loc[missing, ["election_year", "authority_name_raw", "ward_code"]]
            .drop_duplicates()
            .head(),
        )
        merged.loc[missing, "authority_name"] = merged.loc[missing, "authority_name_raw"]

    merged = merged.drop(
        columns=[
            "lad_code_from_lookup",
            "LAD23CD",
            "LAD23NM",
            "RGN23NM",
            "authority_name_raw",
        ],
        errors="ignore",
    )
    return merged


def join_region_commons(
    df: pd.DataFrame,
    lad_region: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()
    df["authority_code"] = df["authority_code"].astype("string")
    merged = df.merge(
        lad_region,
        left_on="authority_code",
        right_on="LAD23CD",
        how="left",
    )
    merged["authority_name"] = merged["LAD23NM"]
    merged["region"] = merged["RGN23NM"]

    missing = merged["authority_code"].isna() | merged["region"].isna()
    if missing.any():
        LOGGER.warning(
            "%s Commons 2022 rows could not be resolved to a region",
            missing.sum(),
        )

    merged = merged.drop(columns=["LAD23CD", "LAD23NM", "RGN23NM"], errors="ignore")
    return merged


def derive_authority_type_and_tier(authority_code: str) -> tuple[str | None, int | None]:
    if pd.isna(authority_code):
        return (None, None)
    if not isinstance(authority_code, str):
        authority_code = str(authority_code)
    if authority_code.startswith("E09"):
        return ("london_borough", 2)
    if authority_code in WEST_YORKSHIRE_CODES:
        return ("west_yorkshire_mb", 3)
    if authority_code.startswith("E08"):
        return ("metropolitan_borough", 1)
    return (None, None)


def apply_authority_type_tier(df: pd.DataFrame) -> pd.DataFrame:
    result = df["authority_code"].apply(
        lambda c: pd.Series(
            derive_authority_type_and_tier(c),
            index=["authority_type", "tier"],
        )
    )
    df["authority_type"] = result["authority_type"]
    df["tier"] = result["tier"].astype("Int64")
    df["authority_type"] = df["authority_type"].astype("string")
    return df


def build_authority_dimension(df: pd.DataFrame) -> pd.DataFrame:
    dim = (
        df[
            [
                "authority_code",
                "authority_name",
                "authority_type",
                "region",
                "tier",
            ]
        ]
        .drop_duplicates(subset=["authority_code"])
        .dropna(subset=["authority_code"])
        .reset_index(drop=True)
    )

    tier1_codes = set(
        dim[
            dim["authority_code"].notna()
            & dim["authority_code"].str.startswith("E08", na=False)
        ]["authority_code"]
    )
    tier1_codes -= WEST_YORKSHIRE_CODES
    tier1_codes -= EXCLUDED_METRO_CODES
    tier2_codes = set(
        dim[dim["authority_code"].str.startswith("E09", na=False)]["authority_code"]
    )
    CITY_OF_LONDON = {"E09000001"}
    tier2_codes -= CITY_OF_LONDON
    tier3_codes = set(WEST_YORKSHIRE_CODES)
    active_codes = tier1_codes | tier2_codes | tier3_codes
    dim["election_active_2026"] = dim["authority_code"].isin(active_codes)
    dim["all_out_2026"] = dim["authority_code"].isin(ALLOUT_CODES)
    dim["notes"] = None
    dim.loc[
        dim["authority_code"].isin(EXCLUDED_METRO_CODES),
        "notes",
    ] = "No 2026 election — excluded from active scope"
    dim.loc[
        dim["all_out_2026"],
        "notes",
    ] = "All-out election 2026 — LGBCE boundary review"

    return dim.sort_values(["tier", "authority_name"]).reset_index(drop=True)


def run_geography():
    lad_region, wl_18, wl_22, wl_11 = load_lookups()
    ward_authority = build_ward_authority_lookup()
    commons_candidates = pd.read_parquet(
        "data/interim/commons_2022_candidates.parquet"
    )[["authority_code", "authority_name_raw"]]
    commons_candidates["authority_code"] = commons_candidates["authority_code"].astype(
        "string"
    )
    df = pd.read_csv(CLEAN_PATH, low_memory=False)

    commons_mask = df["source_dataset"] == "commons_2022"
    dcleapil_mask = df["source_dataset"].str.startswith("dcleapil", na=False)

    assert commons_mask.sum() + dcleapil_mask.sum() == len(df), \
        "Unexpected source_dataset values present during geography join"

    df_dcleapil = df[dcleapil_mask].copy()
    df_commons = df[commons_mask].copy()

    df_dcleapil = join_authority_code_dcleapil(
        df_dcleapil, wl_18, wl_22, lad_region, wl_11, ward_authority
    )
    if len(df_commons) != len(commons_candidates):
        raise AssertionError("Commons interim rows do not match canonical count")
    df_commons["authority_code"] = commons_candidates["authority_code"].values
    df_commons["authority_name_raw"] = commons_candidates[
        "authority_name_raw"
    ].values
    df_commons = join_region_commons(df_commons, lad_region)

    indices = df_dcleapil["__orig_index"].astype(int)
    for col in ["authority_code", "authority_name", "region"]:
        df.loc[indices, col] = df_dcleapil[col].values
        df.loc[df_commons.index, col] = df_commons[col]

    df = apply_authority_type_tier(df)
    dim = build_authority_dimension(df)

    df.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    dim.to_csv(DIM_PATH, index=False, encoding="utf-8")

    LOGGER.info("Geography join complete: %s rows linked, %s authorities written", len(df), len(dim))
    return df, dim


def main():
    logging.basicConfig(level=logging.INFO)
    LOGGER.info("Phase 6 geography join starting")
    run_geography()
    LOGGER.info("Phase 6 geography join finished")


if __name__ == "__main__":
    main()
