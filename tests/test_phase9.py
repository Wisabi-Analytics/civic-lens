import os

import pandas as pd
import pytest

TM = "data/processed/training_metrics.csv"
BA = "data/processed/backtest_actuals_2022.csv"
PST = "data/processed/party_swings_training.csv"
PSB = "data/processed/party_swings_backtest.csv"


@pytest.fixture(scope="module")
def tm():
    return pd.read_csv(TM)


@pytest.fixture(scope="module")
def ba():
    return pd.read_csv(BA)


@pytest.fixture(scope="module")
def pst():
    return pd.read_csv(PST)


@pytest.fixture(scope="module")
def psb():
    return pd.read_csv(PSB)


@pytest.fixture(scope="module")
def dim():
    return pd.read_csv("data/processed/authority_dimension.csv")


def test_all_output_files_exist():
    for path in [TM, BA, PST, PSB]:
        assert os.path.exists(path), f"Missing: {path}"


def test_all_69_authorities_have_borough_rows(tm, ba, dim):
    all_auths = set(dim["authority_code"])
    for label, frame in [("training", tm), ("backtest", ba)]:
        borough_auths = set(frame.loc[frame["computation_level"] == "borough", "authority_code"])
        assert borough_auths == all_auths, f"{label}: missing borough rows for {all_auths - borough_auths}"


def test_training_has_ward_and_borough_rows(tm):
    levels = set(tm["computation_level"].unique())
    assert levels == {"ward", "borough"}


def test_backtest_is_borough_only_under_current_data(ba):
    assert set(ba["computation_level"].unique()) == {"borough"}


def test_active_authority_flag_matches_dimension(tm, ba, dim):
    active_auths = set(dim.loc[dim["election_active_2026"] == True, "authority_code"])
    for frame in [tm, ba]:
        flagged = set(
            frame.loc[
                (frame["computation_level"] == "borough") & (frame["election_active_2026"] == True),
                "authority_code",
            ]
        )
        assert flagged == active_auths


def test_fi_minimum(tm, ba):
    for label, frame in [("training", tm), ("backtest", ba)]:
        for col in [column for column in frame.columns if column.startswith("fi_")]:
            bad = (frame[col].dropna() < 0.99).sum()
            assert bad == 0, f"{label}.{col}: {bad} values below 1.0"


def test_sc_minimum(tm, ba):
    for label, frame in [("training", tm), ("backtest", ba)]:
        bad = (frame["swing_concentration"].dropna() < 0.99).sum()
        assert bad == 0, f"{label}: {bad} SC < 1.0"


def test_training_year_rules(tm):
    ward_rows = tm[tm["computation_level"] == "ward"]
    borough_rows = tm[tm["computation_level"] == "borough"]
    assert set(ward_rows["training_year"].dropna().unique()).issubset({2014, 2015, 2016})
    assert borough_rows["training_year"].isna().all()


def test_borough_seat_change_is_null(tm, ba):
    for frame in [tm, ba]:
        assert frame.loc[frame["computation_level"] == "borough", "seat_change"].isna().all()


def test_vote_shares_in_swing_files(pst, psb):
    for label, frame in [("training", pst), ("backtest", psb)]:
        for col in [column for column in frame.columns if "vote_share" in column]:
            values = frame[col].dropna()
            assert (values >= 0).all() and (values <= 100).all(), f"{label}.{col} outside [0,100]"


def test_party_swing_authority_sets_match(tm, pst, ba, psb):
    tm_computable = set(
        tm.loc[tm["volatility_score"].notna(), "authority_code"]
    )
    ba_computable = set(
        ba.loc[ba["volatility_score"].notna(), "authority_code"]
    )
    assert set(pst["authority_code"]) == tm_computable
    assert set(psb["authority_code"]) == ba_computable
