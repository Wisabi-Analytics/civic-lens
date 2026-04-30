import sys

import pandas as pd
import pandas.testing as pdt

sys.path.insert(0, "src")


AUTH = "reports/tableau_data/tableau_authority_metrics.csv"
PARTY = "reports/tableau_data/tableau_party_swings.csv"
FI = "reports/tableau_data/tableau_fi_timeseries.csv"
KPI = "reports/tableau_data/tableau_kpis.csv"
TM = "data/processed/training_metrics.csv"
BA = "data/processed/backtest_actuals_2022.csv"
CLEAN = "data/processed/clean_election_results.csv"


def test_authority_metrics_match_phase9_borough_metrics():
    auth = pd.read_csv(AUTH)
    tm = pd.read_csv(TM)
    ba = pd.read_csv(BA)

    train = auth[auth["window"] == "2014→2018"].merge(
        tm[tm["computation_level"] == "borough"][
            ["authority_code", "fi_training", "fi_2018", "delta_fi", "volatility_score"]
        ],
        on="authority_code",
        how="left",
        suffixes=("_tableau", "_phase9"),
    )
    back = auth[auth["window"] == "2018→2022"].merge(
        ba[ba["computation_level"] == "borough"][
            ["authority_code", "fi_2018", "fi_2022", "delta_fi", "volatility_score"]
        ],
        on="authority_code",
        how="left",
        suffixes=("_tableau", "_phase9"),
    )

    pdt.assert_series_equal(
        train["fi_start"].round(6), train["fi_training"].round(6), check_names=False
    )
    pdt.assert_series_equal(
        train["fi_end"].round(6), train["fi_2018"].round(6), check_names=False
    )
    pdt.assert_series_equal(
        train["delta_fi_tableau"].round(6),
        train["delta_fi_phase9"].round(6),
        check_names=False,
    )
    pdt.assert_series_equal(
        train["volatility_score_tableau"].round(6),
        train["volatility_score_phase9"].round(6),
        check_names=False,
    )

    pdt.assert_series_equal(
        back["fi_start"].round(6), back["fi_2018"].round(6), check_names=False
    )
    pdt.assert_series_equal(
        back["fi_end"].round(6), back["fi_2022"].round(6), check_names=False
    )
    pdt.assert_series_equal(
        back["delta_fi_tableau"].round(6),
        back["delta_fi_phase9"].round(6),
        check_names=False,
    )
    pdt.assert_series_equal(
        back["volatility_score_tableau"].round(6),
        back["volatility_score_phase9"].round(6),
        check_names=False,
    )


def test_tableau_party_swings_expose_distinct_party_identity_columns():
    party = pd.read_csv(PARTY)
    required = {
        "party_standardised",
        "metric_party_family",
        "challenger_party_family",
        "party_label_norm",
        "challenger_party",
        "is_challenger",
    }
    assert required.issubset(set(party.columns))
    assert party["metric_party_family"].notna().all()
    assert party["party_label_norm"].notna().all()


def test_tableau_party_swings_are_metric_family_normalised():
    party = pd.read_csv(PARTY)
    forbidden = {
        "Labour Party",
        "Labour And Cooperative Party",
        "Reform Uk",
        "Uk Independence Party (Ukip)",
        "UK Independence Party (Ukip)",
        "Brexit Party",
    }
    assert not (forbidden & set(party["metric_party_family"].dropna()))
    assert "LAB" in set(party["metric_party_family"])
    assert "REFORM" in set(party["metric_party_family"])


def test_fi_timeseries_uses_active_rows_not_descriptive_only():
    fi = pd.read_csv(FI)
    clean = pd.read_csv(CLEAN, low_memory=False)
    active = clean[
        (clean["analysis_level"] != "descriptive_only")
        & (clean["authority_code"] != "E09000001")
        & (clean["election_year"].isin([2014, 2015, 2016, 2018, 2022]))
    ]
    expected = (
        active[["authority_code", "election_year"]]
        .drop_duplicates()
        .sort_values(["authority_code", "election_year"])
        .reset_index(drop=True)
    )
    observed = (
        fi[["authority_code", "election_year"]]
        .drop_duplicates()
        .sort_values(["authority_code", "election_year"])
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(observed, expected)


def test_kpis_reflect_corrected_phase9_story():
    kpi = pd.read_csv(KPI).iloc[0]
    assert int(kpi["n_fi_increased"]) == 18
    assert int(kpi["n_comparable"]) == 67
    assert round(float(kpi["median_vol_2018_2022"]), 2) == 22.52
    assert round(float(kpi["median_delta_fi_2018_2022"]), 2) == -0.31
