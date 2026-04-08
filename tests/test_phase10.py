import os
import pickle

import pandas as pd
import pytest

BR = "artifacts/backtest_results.csv"
PKL = "artifacts/error_distributions.pkl"
VICP = "artifacts/london_vi_cap.txt"
CREP = "artifacts/calibration_report.md"
SM = "data/processed/shock_metrics.csv"


@pytest.fixture(scope="module")
def br():
    return pd.read_csv(BR)


@pytest.fixture(scope="module")
def ed():
    with open(PKL, "rb") as fh:
        return pickle.load(fh)


@pytest.fixture(scope="module")
def sm():
    return pd.read_csv(SM)


@pytest.fixture(scope="module")
def dim():
    return pd.read_csv("data/processed/authority_dimension.csv")


@pytest.fixture(scope="module")
def s5_token():
    with open(VICP, "r", encoding="utf-8") as fh:
        return fh.readline().strip()


def test_all_output_files_exist():
    for p in [BR, PKL, VICP, CREP, SM]:
        assert os.path.exists(p), f"Missing: {p}"


def test_backtest_results_has_all_authorities(br, dim):
    assert set(br["authority_code"]) == set(dim["authority_code"])


def test_backtest_results_contains_error_columns(br):
    for metric in ["volatility_score", "delta_fi", "turnout_delta", "swing_concentration"]:
        assert f"{metric}_training" in br.columns
        assert f"{metric}_backtest" in br.columns
        assert f"{metric}_error" in br.columns
        assert f"{metric}_abs_error" in br.columns


def test_error_distributions_structure(ed):
    assert "tier_pools" in ed
    assert "borough_errors" in ed
    assert "fallback_authorities" in ed
    assert ed.get("rng_seed") == 20260430
    assert ed.get("n_iterations") == 2000
    metrics = ed.get("calibrated_metrics", [])
    assert set(metrics) == {"volatility_score", "delta_fi", "turnout_delta", "swing_concentration"}
    for tier in [1, 2, 3]:
        assert tier in ed["tier_pools"]
        for metric in metrics:
            vals = ed["tier_pools"][tier][metric]
            assert len(vals) >= 3, f"Tier {tier} {metric} has only {len(vals)} observations"


def test_london_vi_cap_file_valid(s5_token):
    if s5_token != "S5_REMOVED":
        cap = float(s5_token)
        assert cap > 0
        assert cap < 100


def test_shock_metrics_row_count(sm, dim, s5_token):
    expected_scenarios = 5 if s5_token == "S5_REMOVED" else 6
    assert len(sm) == len(dim) * expected_scenarios


def test_shock_metrics_scenarios(sm, s5_token):
    expected = {"S0", "S1", "S2", "S3", "S4"}
    if s5_token != "S5_REMOVED":
        expected.add("S5")
    assert set(sm["scenario_id"].unique()) == expected


def test_s0_has_zero_shocks(sm):
    s0 = sm[sm["scenario_id"] == "S0"]
    assert (s0["challenger_swing_pp"] == 0.0).all()
    assert (s0["established_swing_pp"] == 0.0).all()
    assert (s0["turnout_shock_pp"] == 0.0).all()


def test_s4_shock_only_deprived(sm):
    s4 = sm[sm["scenario_id"] == "S4"].copy()
    known = s4[s4["imd_decile"].notna()]
    low = known[known["imd_decile"] <= 3]
    high = known[known["imd_decile"] > 3]
    assert (low["turnout_shock_pp"] == 3.0).all()
    assert (high["turnout_shock_pp"] == 0.0).all()


def test_s5_rules(sm, s5_token):
    if s5_token == "S5_REMOVED":
        assert not (sm["scenario_id"] == "S5").any()
        return
    s5 = sm[sm["scenario_id"] == "S5"]
    assert len(s5) > 0
    non_london = s5[s5["tier"] != 2]
    london = s5[s5["tier"] == 2]
    assert non_london["vi_cap"].isna().all()
    assert london["vi_cap"].notna().all()


def test_calibration_report_exists_and_nonempty():
    content = open(CREP, "r", encoding="utf-8").read()
    assert len(content) > 500
    for section in [
        "Summary Statistics",
        "Systematic Biases",
        "Brexit",
        "Fallback Authorities",
        "Disclosure Statement",
    ]:
        assert section in content
