import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "src")

from civic_lens import scenario_model


@pytest.fixture(scope="module")
def generated():
    outputs, logs = scenario_model.run_simulation(write=True)
    return outputs, logs


@pytest.fixture(scope="module")
def outputs(generated):
    return generated[0]


@pytest.fixture(scope="module")
def logs(generated):
    return generated[1]


@pytest.fixture(scope="module")
def dim():
    return pd.read_csv("data/processed/authority_dimension.csv")


@pytest.fixture(scope="module")
def shocks():
    return pd.read_csv("data/processed/shock_metrics.csv")


@pytest.fixture(scope="module")
def error_distributions():
    return scenario_model.load_inputs()[4]


@pytest.fixture(scope="module")
def london_vi_cap():
    return scenario_model._read_london_vi_cap()


def test_exact_row_count(outputs, london_vi_cap):
    expected = 1536 if london_vi_cap is not None else 1280
    assert len(outputs) == expected


def test_authority_scenario_metric_coverage(outputs, dim, london_vi_cap):
    active = set(scenario_model.active_authorities(dim))
    expected_scenarios = set(scenario_model.scenario_ids(london_vi_cap))
    assert outputs["authority_code"].nunique() == 64
    assert set(outputs["authority_code"]) == active
    assert set(outputs["scenario_id"]) == expected_scenarios
    assert set(outputs["metric"]) == set(scenario_model.SIMULATED_METRICS)
    counts = outputs.groupby(["scenario_id", "metric"])["authority_code"].nunique()
    assert (counts == 64).all()


def test_interval_ordering(outputs):
    assert ((outputs["P10"] <= outputs["P50"]) & (outputs["P50"] <= outputs["P90"])).all()


def test_excluded_metrics_absent(outputs):
    assert "vote_share_swing" not in set(outputs["metric"])
    assert "seat_change" not in set(outputs["metric"])
    assert "fragmentation_index" not in set(outputs["metric"])


def test_s3_volatility_point_estimate_threshold(outputs):
    s3 = outputs[(outputs["scenario_id"] == "S3") & (outputs["metric"] == "volatility_score")]
    assert s3["point_estimate"].median() >= 2.0


def test_s4_vote_share_metrics_copy_s0_exactly(outputs):
    s0 = outputs[outputs["scenario_id"] == "S0"].set_index(["authority_code", "metric"])
    s4 = outputs[outputs["scenario_id"] == "S4"].set_index(["authority_code", "metric"])
    for metric in ["delta_fi", "volatility_score", "swing_concentration"]:
        cols = ["P10", "P50", "P90", "point_estimate"]
        pd.testing.assert_frame_equal(
            s4.xs(metric, level="metric")[cols],
            s0.xs(metric, level="metric")[cols],
            check_dtype=False,
        )


def test_s4_turnout_uses_imd_shock(outputs, shocks):
    s4_turnout = outputs[
        (outputs["scenario_id"] == "S4") & (outputs["metric"] == "turnout_delta")
    ][["authority_code", "point_estimate"]]
    s4_shocks = shocks[
        (shocks["scenario_id"] == "S4") & (shocks["election_active_2026"] == True)
    ][["authority_code", "turnout_shock_pp"]]
    merged = s4_turnout.merge(s4_shocks, on="authority_code", how="inner")
    assert len(merged) == 64
    assert np.allclose(merged["point_estimate"], merged["turnout_shock_pp"])


def test_s5_copy_and_cap_rules(outputs, london_vi_cap):
    if london_vi_cap is None:
        assert "S5" not in set(outputs["scenario_id"])
        return
    s0 = outputs[outputs["scenario_id"] == "S0"].set_index(["authority_code", "metric"])
    s5 = outputs[outputs["scenario_id"] == "S5"]
    non_london = s5[s5["tier"] != 2]
    assert (non_london["notes"] == "copied_from_s0").all()
    for _, row in non_london.iterrows():
        source = s0.loc[(row["authority_code"], row["metric"])]
        for col in ["P10", "P50", "P90", "point_estimate"]:
            assert np.isclose(row[col], source[col], rtol=0, atol=1e-9)

    london_vol = s5[(s5["tier"] == 2) & (s5["metric"] == "volatility_score")]
    assert (london_vol["P90"] <= london_vi_cap + 1e-9).all()


def test_interval_width_meets_floor_except_logged_overrides(outputs, logs, error_distributions):
    allowed = {
        (r["scenario_id"], r["authority_code"], r["metric"], r["event_type"])
        for _, r in logs.iterrows()
        if r["event_type"] in {"s5_floor_overridden_by_cap", "metric_lower_bound_overrode_floor"}
    }
    failures = []
    for _, row in outputs.iterrows():
        pool = scenario_model.tier_pool(
            error_distributions, int(row["tier"]), str(row["metric"])
        )
        floor = scenario_model.rmse(pool)
        width = float(row["P90"]) - float(row["P10"])
        cap_key = (
            row["scenario_id"],
            row["authority_code"],
            row["metric"],
            "s5_floor_overridden_by_cap",
        )
        sc_key = (
            row["scenario_id"],
            row["authority_code"],
            row["metric"],
            "metric_lower_bound_overrode_floor",
        )
        if width + 1e-9 < floor and cap_key not in allowed and sc_key not in allowed:
            failures.append((row["scenario_id"], row["authority_code"], row["metric"]))
    assert not failures


def test_swing_concentration_lower_bound(outputs):
    sc = outputs[outputs["metric"] == "swing_concentration"]
    assert (sc["P10"] >= 1.0).all()


def test_turnout_p50_bound(outputs):
    turnout = outputs[outputs["metric"] == "turnout_delta"]
    assert (turnout["P50"].abs() <= 30).all()


def test_party_normalisation_guard(shocks):
    s1 = shocks[(shocks["scenario_id"] == "S1") & (shocks["election_active_2026"] == True)]
    observed = set(s1["challenger_party"].dropna())
    assert not (scenario_model.FORBIDDEN_RAW_PARTY_LABELS & observed)
    assert (s1["challenger_party"] == "LAB").mean() < 0.75


def test_point_estimates_non_null(outputs):
    assert outputs["point_estimate"].notna().all()
    assert outputs[["P10", "P50", "P90"]].notna().all().all()


def test_run_simulation_reproducible_in_same_process():
    out1, log1 = scenario_model.run_simulation(write=False)
    out2, log2 = scenario_model.run_simulation(write=False)
    pd.testing.assert_frame_equal(out1, out2)
    pd.testing.assert_frame_equal(log1, log2)
    assert scenario_model.dataframe_hash(out1) == scenario_model.dataframe_hash(out2)
