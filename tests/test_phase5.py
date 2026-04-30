import pandas as pd
import pytest

from civic_lens.ward_name_utils import clean_ward_name

CSV = "data/processed/clean_election_results.csv"
WARD_LOOKUP_DEC2018 = pd.read_parquet("data/interim/ward_lad_dec2018.parquet")
MANCHESTER_WARD_CODES = set(
    WARD_LOOKUP_DEC2018[
        WARD_LOOKUP_DEC2018["LAD18NM"].str.lower() == "manchester"
    ]["WD18CD"]
)


def test_clean_ward_name_ampersand_with_spaces():
    assert clean_ward_name("Bordesley & Highgate") == "Bordesley And Highgate"


def test_clean_ward_name_no_spaces_around_ampersand():
    assert clean_ward_name("Bordesley&Highgate") == "Bordesleyandhighgate".title()


def test_clean_ward_name_dcleapil_style():
    assert clean_ward_name("Bordesley Highgate") == "Bordesley Highgate"


def test_clean_ward_name_curly_apostrophe():
    assert clean_ward_name("St Mary\u2019s") == "St Mary'S"


def test_clean_ward_name_extra_whitespace():
    assert clean_ward_name("  Wigan  Central  ") == "Wigan Central"


def test_clean_ward_name_null_input():
    assert clean_ward_name(None) == ""
    assert clean_ward_name("") == ""


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV, low_memory=False)


# ── Schema ──────────────────────────────────────────────────────────────────


def test_canonical_columns_present(df):
    EXPECTED = [
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
    assert list(df.columns) == EXPECTED, (
        f"Column mismatch.\nExpected: {EXPECTED}\nGot: {list(df.columns)}"
    )


def test_no_extra_columns(df):
    assert len(df.columns) == 31


def test_no_null_non_nullable_fields(df):
    NON_NULL = [
        "election_year",
        "election_date",
        "source_dataset",
        "data_source_era",
        "ward_name_raw",
        "ward_name_clean",
        "candidate_name",
        "party_raw",
        "party_standardised",
        "party_group",
        "is_ilp",
        "elected",
        "seats_contested",
        "seats_won",
        "analysis_level",
        "harmonisation_status",
    ]
    for col in NON_NULL:
        null_count = df[col].isna().sum()
        assert null_count == 0, (
            f"Non-nullable column '{col}' has {null_count} null rows"
        )


# ── Year and date integrity ─────────────────────────────────────────────────


def test_election_years_in_scope(df):
    assert set(df["election_year"].unique()) == {2014, 2015, 2016, 2018, 2022}


def test_election_dates_correct(df):
    DATE_MAP = {
        2014: "2014-05-22",
        2015: "2015-05-07",
        2016: "2016-05-05",
        2018: "2018-05-03",
        2022: "2022-05-05",
    }
    for yr, expected_date in DATE_MAP.items():
        dates = df[df["election_year"] == yr]["election_date"].unique()
        assert len(dates) == 1, f"Year {yr} has multiple dates: {dates}"
        assert dates[0] == expected_date, (
            f"Year {yr}: expected {expected_date}, got {dates[0]}"
        )


# ── Row counts ───────────────────────────────────────────────────────────────


def test_total_row_count_plausible(df):
    assert 45_000 < len(df) < 52_000, (
        f"Total row count {len(df)} outside expected range"
    )


def test_dcleapil_year_row_counts(df):
    dcl = df[df["source_dataset"].str.startswith("dcleapil")]
    counts = dcl.groupby("election_year").size()
    expected = {
        2014: 10619,
        2015: 4104,
        2016: 3968,
        2018: 10597,
        2022: 9831,
    }
    for year, value in expected.items():
        assert abs(counts.get(year, 0) - value) <= 100, (
            f"Year {year}: expected ~{value} rows, got {counts.get(year, 0)}"
        )


def test_commons_2022_row_count(df):
    commons = df[df["source_dataset"] == "commons_2022"]
    assert abs(len(commons) - 9571) <= 50, (
        f"Commons 2022 rows: expected ~9571, got {len(commons)}"
    )


# ── Source dataset values ────────────────────────────────────────────────────


def test_source_dataset_values(df):
    valid = {
        "dcleapil_2014",
        "dcleapil_2015",
        "dcleapil_2016",
        "dcleapil_2018",
        "dcleapil_2022",
        "commons_2022",
    }
    actual = set(df["source_dataset"].unique())
    assert actual == valid, f"Unexpected source_dataset values: {actual - valid}"


def test_data_source_era_correct(df):
    assert (df[df["election_year"] <= 2015]["data_source_era"] == "leap_only").all()
    assert (df[df["election_year"] >= 2016]["data_source_era"] == "dc_leap").all()


# ── Party standardisation ────────────────────────────────────────────────────


def test_no_raw_nr_party_ids_in_standardised(df):
    assert not df["party_standardised"].str.startswith("NR_", na=False).any()


def test_no_unknown_party_groups(df):
    valid_groups = {"Major", "Minor", "ILP", "Independent", "Unknown"}
    actual = set(df["party_group"].dropna().unique())
    unexpected = actual - valid_groups
    assert not unexpected, f"Unexpected party_group values: {unexpected}"


def test_is_ilp_is_boolean(df):
    assert df["is_ilp"].dtype == bool or df["is_ilp"].isin([True, False]).all()


def test_ilp_flag_consistent_with_group(df):
    ilp_true = df[df["is_ilp"] == True]
    assert (ilp_true["party_group"] == "ILP").all(), (
        "is_ilp=True rows must have party_group='ILP'"
    )


def test_yorks_party_present(df):
    yorks_rows = df[df["party_raw"].str.upper().str.contains("YORKS", na=False)]
    assert len(yorks_rows) > 0, "YORKS (Yorkshire Party) rows not found — should not be dropped"


# ── Vote share and turnout ───────────────────────────────────────────────────


def test_vote_share_range(df):
    valid = df["vote_share"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all(), (
        f"vote_share out of range [0,100]: {valid[~valid.between(0,100)]}"
    )


def test_vote_share_null_only_for_uncontested(df):
    null_vs = df[df["vote_share"].isna()]
    allowed = (
        null_vs["analysis_level"].isin(["borough_only", "descriptive_only"])
        | null_vs["votes"].isna()
        | null_vs["total_valid_votes"].isna()
        | (null_vs["total_valid_votes"] == 0)
    )
    assert allowed.all(), (
        f"{(~allowed).sum()} rows have null vote_share but are not borough_only/descriptive_only"
    )


def test_turnout_pct_range_after_correction(df):
    over_100 = df[df["turnout_pct"].notna() & (df["turnout_pct"] > 100)]
    if len(over_100) > 0:
        flagged = over_100["notes"].str.contains("turnout_over_100", na=False)
        assert flagged.all(), (
            f"{(~flagged).sum()} rows with turnout_pct > 100 not flagged in notes"
        )


def test_turnout_pct_not_negative(df):
    neg = df[df["turnout_pct"].notna() & (df["turnout_pct"] < 0)]
    assert len(neg) == 0, f"{len(neg)} rows with negative turnout_pct"


# ── analysis_level ──────────────────────────────────────────────────────────


def test_analysis_level_values(df):
    valid = {"ward", "borough_only", "borough_fallback", "descriptive_only"}
    actual = set(df["analysis_level"].unique())
    assert actual.issubset(valid), f"Unexpected analysis_level values: {actual - valid}"


def test_uncontested_wards_flagged_borough_only(df):
    uncontested = df[df["notes"].str.contains("uncontested", na=False)]
    assert (uncontested["analysis_level"] == "borough_only").all()


def test_superseded_rows_flagged_descriptive_only(df):
    superseded = df[df["notes"].str.contains("superseded_by_commons_2022", na=False)]
    assert (superseded["analysis_level"] == "descriptive_only").all()


def test_null_ward_code_flagged_borough_only(df):
    null_wc = df[df["ward_code"].isna() & (df["source_dataset"] != "commons_2022")]
    if len(null_wc) > 0:
        assert (null_wc["analysis_level"] == "borough_only").all()


# ── Seats and elected ───────────────────────────────────────────────────────


def test_seats_won_lte_seats_contested(df):
    invalid = df[df["seats_won"] > df["seats_contested"]]
    assert len(invalid) == 0, (
        f"{len(invalid)} rows where seats_won > seats_contested"
    )


def test_seats_won_derived_from_elected(df):
    mismatch = df[
        (df["elected"] == True) & (df["seats_won"] != 1)
        | (df["elected"] == False) & (df["seats_won"] != 0)
    ]
    assert len(mismatch) == 0, f"{len(mismatch)} rows where seats_won != int(elected)"


def test_seats_contested_in_valid_range(df):
    invalid = df[~df["seats_contested"].isin([1, 2, 3])]
    assert len(invalid) == 0, (
        f"seats_contested values outside {{1,2,3}}: {df['seats_contested'].unique()}"
    )


# ── Source conflict resolution ───────────────────────────────────────────────


def test_no_dcleapil_2022_rows_active_where_commons_covers(df):
    commons_keys = {
        tuple(x)
        for x in df[df["source_dataset"] == "commons_2022"][
            ["ward_code", "party_standardised"]
        ]
        .dropna()
        .itertuples(index=False, name=None)
    }
    mask = (
        (df["source_dataset"] == "dcleapil_2022")
        & (df["analysis_level"] != "descriptive_only")
    )
    tuples = [
        (wc, ps)
        for wc, ps in zip(df["ward_code"], df["party_standardised"])
    ]
    overlap = df[mask & pd.Series(tuples).isin(commons_keys)]
    assert len(overlap) == 0, (
        "Active DCLEAPIL 2022 rows for wards covered by Commons should not exist"
    )


# ── Ward name standardisation ────────────────────────────────────────────────


def test_ward_name_clean_no_ampersands(df):
    has_amp = df["ward_name_clean"].str.contains("&", na=False)
    assert not has_amp.any(), (
        f"{has_amp.sum()} ward_name_clean values still contain '&'"
    )


def test_ward_name_clean_not_null(df):
    assert df["ward_name_clean"].notna().all()
    assert (df["ward_name_clean"] != "").all()


# ── Leap_only electorate nulls ───────────────────────────────────────────────


def test_leap_only_higher_null_rates_acceptable(df):
    for yr in [2014, 2015]:
        sub = df[df["election_year"] == yr]
        null_rate = sub["electorate"].isna().mean()
        assert null_rate < 0.15, (
            f"Year {yr}: electorate null rate {null_rate:.1%} exceeds expected ceiling (15%)"
        )
        print(
            f"INFO: Year {yr} electorate null rate = {null_rate:.1%} (expected ~4-7%)"
        )


# ── Spot-check known values ──────────────────────────────────────────────────


def test_sunderland_pallion_2018_votes(df):
    row = df[
        (df["election_year"] == 2018)
        & (df["ward_name_raw"].str.lower() == "pallion")
        & (df["source_dataset"] == "dcleapil_2018")
    ]
    assert len(row) > 0, "Sunderland/Pallion 2018 not found"
    assert (row["votes"] == 1251).any(), (
        f"Sunderland/Pallion 2018 votes: expected 1251, got {row['votes'].values}"
    )


def test_manchester_2018_vote_share_derived(df):
    assert MANCHESTER_WARD_CODES, "Manchester ward lookup missing"
    manc = df[
        (df["election_year"] == 2018)
        & df["ward_code"].isin(MANCHESTER_WARD_CODES)
        & df["votes"].notna()
        & df["total_valid_votes"].notna()
    ]
    assert len(manc) > 0, "Manchester 2018 not found"
    assert manc["vote_share"].notna().all(), (
        "Manchester 2018: vote_share null where votes/total_valid_votes present"
    )
    derived = manc["votes"] / manc["total_valid_votes"] * 100
    diff = (manc["vote_share"] - derived).abs()
    assert (diff < 0.01).all(), (
        f"Manchester 2018: vote_share not matching derived value (max diff: {diff.max():.4f})"
    )
