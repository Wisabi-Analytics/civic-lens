import pandas as pd
import pytest

CONC_PATH = "data/processed/concordance_table.csv"
CSV_PATH = "data/processed/clean_election_results.csv"


@pytest.fixture(scope="module")
def conc() -> pd.DataFrame:
    return pd.read_csv(CONC_PATH)


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH, low_memory=False)


def test_concordance_required_columns(conc: pd.DataFrame) -> None:
    required = {
        "authority_code", "authority_name", "ward_code_training",
        "ward_code_2018", "ward_code_2022", "ward_name_clean",
        "match_method", "confidence", "change_type",
        "analysis_level", "fallback_reason",
    }
    assert required.issubset(set(conc.columns))


def test_concordance_match_method_values(conc: pd.DataFrame) -> None:
    valid = {"exact_code", "name_matched", "reviewed", "borough_fallback", "uncalibrated"}
    assert set(conc["match_method"].unique()).issubset(valid)


def test_concordance_change_type_values(conc: pd.DataFrame) -> None:
    valid = {"stable", "split", "merge", "all_out_lgbce", "unmatched", "uncalibrated"}
    actual = set(conc["change_type"].dropna().unique())
    assert actual.issubset(valid)


def test_concordance_analysis_level_values(conc: pd.DataFrame) -> None:
    valid = {"ward", "borough_fallback", "borough_only"}
    actual = set(conc["analysis_level"].dropna().unique())
    assert actual.issubset(valid)


def test_no_silent_nulls_in_concordance(conc: pd.DataFrame) -> None:
    both_null = conc["ward_code_2018"].isna() & conc["ward_code_training"].isna() & conc["ward_code_2022"].isna()
    assert not both_null.any()


def test_exact_code_confidence(conc: pd.DataFrame) -> None:
    exact = conc[conc["match_method"] == "exact_code"]
    assert (exact["confidence"] == "high").all()


def test_stable_analysis_level(conc: pd.DataFrame) -> None:
    stable = conc[conc["change_type"] == "stable"]
    assert (stable["analysis_level"] == "ward").all()


def test_splits_merges_fallback(conc: pd.DataFrame) -> None:
    sm = conc[conc["change_type"].isin({"split", "merge"})]
    assert (sm["analysis_level"] == "borough_fallback").all()


def test_all_out_2026_flagged(conc: pd.DataFrame) -> None:
    all_out_codes = {"E08000016", "E08000025", "E08000013", "E08000033", "E08000026", "E08000034"}
    rows = conc[conc["authority_code"].isin(all_out_codes)]
    assert len(rows) > 0
    assert (rows["change_type"] == "all_out_lgbce").any()


def test_concordance_match_rate(conc: pd.DataFrame) -> None:
    training = conc[conc["ward_code_training"].notna()]
    matched = len(training[training["match_method"].isin({"exact_code", "name_matched"})])
    match_pct = matched / len(training) * 100
    assert match_pct >= 50, f"Ward match rate {match_pct:.1f}% below 50%"


def test_no_unmatched_harmonisation_status(df: pd.DataFrame) -> None:
    still_default = df[(df["harmonisation_status"] == "unmatched") & df["ward_code"].notna()]
    assert len(still_default) == 0


def test_concordance_change_type_populated(df: pd.DataFrame) -> None:
    has_ward = df["ward_code"].notna()
    nulls = df[has_ward & df["concordance_change_type"].isna()]
    assert len(nulls) == 0


def test_analysis_level_values(df: pd.DataFrame) -> None:
    valid = {"ward", "borough_only", "descriptive_only"}
    actual = set(df["analysis_level"].dropna().unique())
    assert actual.issubset(valid)


def test_descriptive_only_preserved(df: pd.DataFrame) -> None:
    desc = df[df["notes"].str.contains("superseded_by_commons_2022", na=False)]
    assert (desc["analysis_level"] == "descriptive_only").all()


def test_row_count(df: pd.DataFrame) -> None:
    assert len(df) == 48690, f"Unexpected row count {len(df)}"


def test_uncontested_borough_only(df: pd.DataFrame) -> None:
    uncontested = df[df["notes"].str.contains("uncontested", na=False)]
    assert (uncontested["analysis_level"] == "borough_only").all()


def test_harmonisation_status_values(df: pd.DataFrame) -> None:
    valid = {"matched", "name_matched", "reviewed", "fallback"}
    actual = set(df["harmonisation_status"].dropna().unique())
    assert actual.issubset(valid)


def test_stable_rows_ward_level(df: pd.DataFrame) -> None:
    stable = df[df["concordance_change_type"] == "stable"]
    non_ward = stable[~stable["analysis_level"].isin({"ward", "descriptive_only"})]
    assert len(non_ward) == 0
