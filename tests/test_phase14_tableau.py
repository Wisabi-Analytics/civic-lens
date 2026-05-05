import sys

import pandas as pd
import pytest

sys.path.insert(0, "src")

from civic_lens import export_phase14_tableau as phase14


@pytest.fixture(scope="module")
def generated_exports():
    phase14.write_exports()
    outputs = pd.read_csv(phase14.TABLEAU / "tableau_scenario_outputs.csv")
    kpis = pd.read_csv(phase14.TABLEAU / "tableau_scenario_kpis.csv")
    rankings = pd.read_csv(phase14.TABLEAU / "tableau_scenario_rankings.csv")
    intervals = pd.read_csv(phase14.TABLEAU / "tableau_scenario_intervals.csv")
    log_summary = pd.read_csv(phase14.TABLEAU / "tableau_scenario_log_summary.csv")
    return outputs, kpis, rankings, intervals, log_summary


@pytest.fixture(scope="module")
def outputs(generated_exports):
    return generated_exports[0]


@pytest.fixture(scope="module")
def kpis(generated_exports):
    return generated_exports[1]


@pytest.fixture(scope="module")
def rankings(generated_exports):
    return generated_exports[2]


@pytest.fixture(scope="module")
def intervals(generated_exports):
    return generated_exports[3]


@pytest.fixture(scope="module")
def log_summary(generated_exports):
    return generated_exports[4]


def test_model_lock_and_source_hash_are_validated():
    outputs, logs, dim, centroids, lock, london_vi_cap, outputs_sha = (
        phase14.load_validated_sources()
    )
    assert len(outputs) == 1536
    assert outputs["authority_code"].nunique() == 64
    assert outputs_sha == phase14.LOCKED_SCENARIO_OUTPUTS_SHA256
    assert lock.status == "LOCKED"
    assert lock.scenario_definitions_sha == phase14.LOCKED_SCENARIO_DEFINITIONS_SHA
    assert phase14.git_hash_object(phase14.SCENARIO_DEFINITIONS) == (
        phase14.LOCKED_SCENARIO_DEFINITIONS_SHA
    )
    assert london_vi_cap == pytest.approx(39.445534)
    assert not logs["event_type"].isin(phase14.BLOCKING_EVENTS).any()
    assert not dim.empty
    assert not centroids.empty


def test_tableau_scenario_outputs_shape_and_columns(outputs):
    required = {
        "scenario_id",
        "scenario_label",
        "scenario_order",
        "authority_code",
        "authority_name",
        "tier",
        "tier_label",
        "region",
        "authority_type",
        "election_active_2026",
        "all_out_2026",
        "metric",
        "metric_label",
        "metric_order",
        "P10",
        "P50",
        "P90",
        "interval_width",
        "uncertainty_asymmetry",
        "point_estimate",
        "notes",
        "lat",
        "lon",
        "is_london",
        "is_s5_copy",
        "is_copied_from_s0",
        "is_turnout_only_s4",
        "is_s5_london_cap_applicable",
        "is_s5_london_cap_binding",
        "london_vi_cap",
        "source_artifact_sha256",
        "model_version_sha",
        "scenario_definitions_sha",
        "freeze_timestamp_utc",
    }
    assert len(outputs) == 1536
    assert required.issubset(outputs.columns)
    assert outputs["authority_code"].nunique() == 64
    assert set(outputs["scenario_id"]) == set(phase14.SCENARIO_LABELS)
    assert set(outputs["metric"]) == set(phase14.METRIC_LABELS)


def test_labels_and_metadata_are_complete(outputs):
    assert outputs["scenario_label"].notna().all()
    assert outputs["metric_label"].notna().all()
    assert outputs["tier_label"].notna().all()
    assert outputs["source_artifact_sha256"].nunique() == 1
    assert outputs["source_artifact_sha256"].iloc[0] == phase14.LOCKED_SCENARIO_OUTPUTS_SHA256
    assert outputs["scenario_definitions_sha"].nunique() == 1
    assert outputs["scenario_definitions_sha"].iloc[0] == phase14.LOCKED_SCENARIO_DEFINITIONS_SHA
    assert outputs["model_version_sha"].nunique() == 1
    assert outputs["freeze_timestamp_utc"].nunique() == 1
    assert outputs["lat"].notna().all()
    assert outputs["lon"].notna().all()
    assert outputs["region"].notna().all()
    assert outputs["authority_type"].notna().all()


def test_interval_ordering_and_derived_fields(outputs):
    assert ((outputs["P10"] <= outputs["P50"]) & (outputs["P50"] <= outputs["P90"])).all()
    assert (outputs["interval_width"].round(10) == (outputs["P90"] - outputs["P10"]).round(10)).all()
    expected_asymmetry = (outputs["P90"] - outputs["P50"]) - (outputs["P50"] - outputs["P10"])
    assert (outputs["uncertainty_asymmetry"].round(10) == expected_asymmetry.round(10)).all()


def test_s5_copy_and_cap_flags(outputs):
    s5 = outputs[outputs["scenario_id"] == "S5"]
    non_london = s5[~s5["is_london"]]
    london_vol = s5[s5["is_london"] & (s5["metric"] == "volatility_score")]
    assert len(s5) == 256
    assert non_london["is_s5_copy"].all()
    assert non_london["is_copied_from_s0"].all()
    assert london_vol["is_s5_london_cap_applicable"].all()
    assert (london_vol["P90"] <= london_vol["london_vi_cap"] + 1e-9).all()
    if not (pd.read_csv(phase14.SCENARIO_LOG)["event_type"] == "s5_vi_capped").any():
        assert not outputs["is_s5_london_cap_binding"].any()


def test_s4_turnout_only_flags(outputs):
    s4 = outputs[outputs["scenario_id"] == "S4"]
    assert s4[s4["metric"] == "turnout_delta"]["is_turnout_only_s4"].all()
    assert not s4[s4["metric"] != "turnout_delta"]["is_turnout_only_s4"].any()
    assert s4[s4["metric"] != "turnout_delta"]["is_copied_from_s0"].all()


def test_kpis_reflect_locked_artifact(kpis):
    row = kpis.iloc[0]
    assert int(row["n_rows"]) == 1536
    assert int(row["n_authorities"]) == 64
    assert int(row["n_scenarios"]) == 6
    assert int(row["n_metrics"]) == 4
    assert row["scenario_outputs_sha256"] == phase14.LOCKED_SCENARIO_OUTPUTS_SHA256
    assert row["scenario_definitions_sha"] == phase14.LOCKED_SCENARIO_DEFINITIONS_SHA
    assert int(row["n_validation_failures"]) == 0
    assert int(row["n_interval_ordering_violations"]) == 0
    assert int(row["n_tier_pool_too_small"]) == 0
    assert float(row["max_s5_london_vol_p90"]) <= float(row["s5_cap"]) + 1e-9
    assert float(row["s3_median_vol_point_estimate"]) >= 2.0


def test_rankings_and_intervals_are_usable(rankings, intervals):
    expected_rankings = {
        "top_volatility_p50",
        "widest_volatility_interval",
        "s3_top_volatility_point_estimate",
        "s5_london_vs_s0",
    }
    assert expected_rankings.issubset(set(rankings["ranking_type"]))
    assert rankings["rank"].notna().all()
    assert len(intervals) == 1536
    assert intervals["interval_width"].notna().all()


def test_log_summary_has_no_blocking_events(log_summary):
    if log_summary.empty:
        return
    blocking = log_summary[log_summary["event_type"].isin(phase14.BLOCKING_EVENTS)]
    assert blocking.empty


def test_audit_markdown_created():
    assert phase14.AUDIT_PATH.exists()
    text = phase14.AUDIT_PATH.read_text(encoding="utf-8")
    assert "Phase 14 Scenario Audit" in text
    assert "scenario analysis, not a forecast" in text
    assert "S5 London Cap Check" in text
