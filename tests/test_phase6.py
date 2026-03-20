import pandas as pd
import pytest

DIM = "data/processed/authority_dimension.csv"
CSV = "data/processed/clean_election_results.csv"


@pytest.fixture(scope="module")
def dim():
    return pd.read_csv(DIM)


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV, low_memory=False)


def test_dim_required_columns(dim):
    required = {
        "authority_code",
        "authority_name",
        "authority_type",
        "region",
        "tier",
        "election_active_2026",
        "all_out_2026",
        "notes",
    }
    assert required.issubset(set(dim.columns))


def test_dim_tier1_active_count(dim):
    t1 = dim[
        (dim["election_active_2026"] == True)
        & dim["authority_code"].str.startswith("E08", na=False)
        & dim["tier"].isin([1, 3])
    ]
    assert len(t1) == 32, (
        f"Tier 1 active: expected 32, got {len(t1)}\n{t1['authority_name'].tolist()}"
    )


def test_dim_tier2_count(dim):
    t2 = dim[(dim["tier"] == 2) & (dim["authority_code"] != "E09000001")]
    assert len(t2) == 32, f"Tier 2: expected 32, got {len(t2)}"


def test_dim_tier3_count(dim):
    t3 = dim[dim["tier"] == 3]
    assert len(t3) == 5, f"Tier 3: expected 5, got {len(t3)}\n{t3['authority_name'].tolist()}"


def test_dim_excluded_not_active(dim):
    EXCLUDED = {"E08000017", "E08000012", "E08000015", "E08000018"}
    excluded_rows = dim[dim["authority_code"].isin(EXCLUDED)]
    assert len(excluded_rows) > 0, "Excluded boroughs not found in dimension table"
    assert not excluded_rows["election_active_2026"].any()


def test_dim_west_yorkshire_typed_correctly(dim):
    WY = {"E08000032", "E08000033", "E08000034", "E08000035", "E08000036"}
    wy = dim[dim["authority_code"].isin(WY)]
    assert len(wy) == 5
    assert (wy["authority_type"] == "west_yorkshire_mb").all()
    assert (wy["tier"] == 3).all()


def test_dim_authority_types_valid(dim):
    valid = {"metropolitan_borough", "london_borough", "west_yorkshire_mb"}
    actual = set(dim["authority_type"].dropna().unique())
    assert actual.issubset(valid), f"Unexpected types: {actual - valid}"


def test_dim_no_null_codes(dim):
    assert dim["authority_code"].notna().all()


def test_dim_all_out_flagged(dim):
    metro_all_out = dim[(dim["tier"] == 1) & (dim["all_out_2026"] == True)]
    assert len(metro_all_out) >= 3
    confirmed = {"E08000016", "E08000025", "E08000013"}
    found = set(dim[dim["all_out_2026"] == True]["authority_code"])
    missing = confirmed - found
    assert not missing, f"Confirmed all-out boroughs not flagged: {missing}"


def test_geography_columns_present(df):
    for col in ["authority_code", "authority_name", "authority_type", "region", "tier"]:
        assert col in df.columns, f"Missing column: {col}"


def test_authority_code_format(df, dim):
    active_codes = set(dim[dim["election_active_2026"] == True]["authority_code"])
    codes = df[df["authority_code"].isin(active_codes)]["authority_code"].dropna()
    valid = codes.str.match(r"^E0[89]\d{6}$")
    assert valid.all()


def test_authority_type_values(df):
    valid = {"metropolitan_borough", "london_borough", "west_yorkshire_mb"}
    actual = set(df["authority_type"].dropna().unique())
    assert actual.issubset(valid)


def test_tier_values(df):
    actual = set(df["tier"].dropna().unique())
    assert actual.issubset({1, 2, 3}), f"Unexpected tier values: {actual}"


def test_london_boroughs_are_tier2(df):
    london = df[df["authority_code"].str.startswith("E09", na=False)]
    assert (london["tier"] == 2).all()
    assert (london["authority_type"] == "london_borough").all()


def test_west_yorkshire_are_tier3(df):
    WY = {"E08000032", "E08000033", "E08000034", "E08000035", "E08000036"}
    wy = df[df["authority_code"].isin(WY)]
    assert len(wy) > 0
    assert (wy["tier"] == 3).all()
    assert (wy["authority_type"] == "west_yorkshire_mb").all()


def test_excluded_boroughs_present_in_data_but_not_tier_null(df):
    EXCLUDED = {"E08000017", "E08000012", "E08000015", "E08000018"}
    excl_rows = df[df["authority_code"].isin(EXCLUDED)]
    assert len(excl_rows) > 0
    assert (excl_rows["tier"] == 1).all()


def test_region_populated_for_in_scope_rows(df):
    active_types = {"metropolitan_borough", "london_borough", "west_yorkshire_mb"}
    in_scope = df[df["authority_type"].isin(active_types)]
    null_region = in_scope["region"].isna().sum()
    assert null_region == 0, f"{null_region} in-scope rows have null region"


def test_authority_name_consistent_with_code(df):
    name_per_code = df.groupby("authority_code")["authority_name"].nunique()
    inconsistent = name_per_code[name_per_code > 1]
    assert len(inconsistent) == 0, f"authority_code maps to multiple names: {inconsistent.index.tolist()}"


def test_dcleapil_rows_have_authority_code(df, dim):
    dcl = df[df["source_dataset"].str.startswith("dcleapil", na=False)]
    active_codes = set(dim[dim["election_active_2026"] == True]["authority_code"])
    dcl_active = dcl[dcl["authority_code"].isin(active_codes)]
    null_pct = dcl_active["authority_code"].isna().mean()
    assert null_pct < 0.01, \
        f"DCLEAPIL rows with null authority_code: {null_pct:.1%} (expected <1%)"


def test_scope_verify_script_passes():
    import subprocess, sys

    result = subprocess.run(
        [sys.executable, "src/civic_lens/scope_verify.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"scope_verify.py failed:\n{result.stdout}\n{result.stderr}"
